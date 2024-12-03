from typing import List, Dict, Optional, AsyncIterator, Any
from pydantic_ai import Agent
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime
from src.models import BillAnalysis, BillSection, LegislativeImpact, Citation, Amendment
from dotenv import load_dotenv
import os
import tiktoken
import json
import re

# Load environment variables
load_dotenv()

class AnalysisTask(BaseModel):
    """Represents a single analysis task for a bill section"""
    section_text: str
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: int = Field(default=1, ge=1, le=5)

class AnalysisResult(BaseModel):
    """Result of analyzing a section of the bill"""
    section: BillSection
    confidence_score: float = Field(..., ge=0, le=1)
    analysis_metadata: Dict[str, Any]
    processing_time: float

class BillAnalyzer:
    def __init__(
        self,
        model_name: str = "gpt-4",
        max_concurrent_tasks: int = 3,
        cache_results: bool = True
    ):
        self.agent = Agent(
            f"openai:{model_name}",
            system_prompt="""You are an expert legislative analyst specializing in analyzing complex congressional bills.
            Focus on identifying key impacts, funding allocations, and cross-references between sections.
            
            For each section, you must:
            1. Extract the section number and title
            2. Provide a clear summary
            3. Identify key points and defined terms
            4. List any funding amounts with their purposes
            5. Note cross-references to other sections
            6. Analyze potential impacts on different sectors
            
            Be precise with numbers and maintain context between sections."""
        )
        self.sections_queue = asyncio.Queue()
        self.max_concurrent_tasks = max_concurrent_tasks
        self._section_context = ""
        self.cache_results = cache_results
        self.tokenizer = tiktoken.encoding_for_model(model_name)
        self.max_tokens = 6000  # Leave room for response
        
    def _count_tokens(self, text: str) -> int:
        return len(self.tokenizer.encode(text))
    
    def _split_section(self, text: str, max_tokens: int) -> list[str]:
        """Split section into chunks that fit within token limit"""
        tokens = self.tokenizer.encode(text)
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        # Try to split on paragraph boundaries
        paragraphs = text.split("\n\n")
        
        for para in paragraphs:
            para_tokens = self.tokenizer.encode(para)
            if current_tokens + len(para_tokens) > max_tokens:
                if current_chunk:
                    chunks.append(self.tokenizer.decode(current_chunk))
                    current_chunk = []
                    current_tokens = 0
                
                # If paragraph itself is too long, split it into sentences
                if len(para_tokens) > max_tokens:
                    sentences = para.split(". ")
                    for sent in sentences:
                        sent_tokens = self.tokenizer.encode(sent + ".")
                        if current_tokens + len(sent_tokens) > max_tokens:
                            if current_chunk:
                                chunks.append(self.tokenizer.decode(current_chunk))
                                current_chunk = []
                                current_tokens = 0
                        current_chunk.extend(sent_tokens)
                        current_tokens += len(sent_tokens)
                else:
                    current_chunk.extend(para_tokens)
                    current_tokens = len(para_tokens)
            else:
                current_chunk.extend(para_tokens)
                current_tokens += len(para_tokens)
        
        if current_chunk:
            chunks.append(self.tokenizer.decode(current_chunk))
        
        return chunks

    async def add_section_for_analysis(self, section_text: str, context: Dict[str, Any]):
        """Add a section to be analyzed"""
        await self.sections_queue.put((section_text, context))
        
    async def analyze_sections(self) -> AsyncIterator[BillSection]:
        """Process all queued sections and yield results as they complete"""
        tasks = []
        while not self.sections_queue.empty() or tasks:
            # Start new tasks up to max_concurrent_tasks
            while len(tasks) < self.max_concurrent_tasks and not self.sections_queue.empty():
                task_data = await self.sections_queue.get()
                if isinstance(task_data, tuple) and len(task_data) == 2:
                    section_text, context = task_data
                else:
                    section_text = task_data
                    context = {}
                task = asyncio.create_task(self._analyze_section_task(section_text, context))
                tasks.append(task)
            
            if not tasks:
                break
            
            # Wait for any task to complete
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            
            # Handle completed tasks
            for task in done:
                try:
                    result = await task
                    yield result
                except Exception as e:
                    print(f"Task failed: {str(e)}")
                tasks = list(pending)  # Update tasks list

    async def _analyze_section_task(self, section_text: str, context: Dict[str, Any]) -> BillSection:
        """Analyze a single section of the bill"""
        # Check if section needs to be split
        section_tokens = self._count_tokens(section_text)
        if section_tokens > self.max_tokens:
            chunks = self._split_section(section_text, self.max_tokens)
            # Analyze each chunk and merge results
            chunk_results = []
            for i, chunk in enumerate(chunks):
                chunk_prompt = f"""Analyze this PART {i+1} of {len(chunks)} of the bill section and return a structured analysis following the exact schema below.
                Previous sections context: {self._section_context}
                
                SECTION TEXT:
                {chunk}
                
                Return a JSON object with this exact structure:
                {{
                    "section_type": "section",
                    "number": "string (section number)",
                    "title": "string (section title)",
                    "content": "string (full section text)",
                    "summary": "string (brief summary of purpose and impact)",
                    "key_points": ["list of key points"],
                    "defined_terms": {{"term": "definition"}} (optional),
                    "impacts": [
                        {{
                            "sector": "string (affected sector)",
                            "impact_level": "integer 1-5 (1=minimal, 5=major)",
                            "description": "string (detailed impact description)",
                            "estimated_cost": "string (optional, e.g. '$1 billion')",
                            "timeline": "string (e.g. 'Effective from 2024', 'Phased over 5 years')",
                            "affected_groups": ["list of affected stakeholders"]
                        }}
                    ],
                    "referenced_sections": ["list of referenced section numbers"] (optional),
                    "funding_amounts": {{"purpose": "amount as number or description"}} (optional)
                }}
                
                IMPORTANT:
                1. All fields are required unless marked (optional)
                2. For impact_level, use 1-5 scale where:
                   1 = Minimal impact
                   2 = Minor impact
                   3 = Moderate impact
                   4 = Significant impact
                   5 = Major impact
                3. Timeline must specify when provisions take effect
                4. Affected_groups should list specific stakeholders
                5. For funding_amounts, use either numeric values (e.g., 500000000) or descriptive text (e.g., "15% of adjusted income")
                
                Return ONLY the JSON object, no additional text or explanations."""
                
                try:
                    response = await self.agent.run(chunk_prompt)
                    fixed_json = self._fix_json_response(response.data)
                    chunk_result = BillSection.model_validate_json(fixed_json)
                    chunk_results.append(chunk_result)
                except Exception as e:
                    print(f"Error analyzing section chunk {i+1}: {str(e)}")
                    raise
            
            # Merge chunk results
            merged_result = chunk_results[0]
            for chunk in chunk_results[1:]:
                merged_result.content += "\n\n" + chunk.content
                merged_result.summary += " " + chunk.summary
                merged_result.key_points.extend(chunk.key_points)
                merged_result.defined_terms.update(chunk.defined_terms)
                merged_result.impacts.extend(chunk.impacts)
                merged_result.referenced_sections.extend(chunk.referenced_sections)
                if chunk.funding_amounts:
                    if not merged_result.funding_amounts:
                        merged_result.funding_amounts = {}
                    merged_result.funding_amounts.update(chunk.funding_amounts)
            
            return merged_result
        
        else:
            prompt = f"""Analyze this bill section and return a structured analysis following the exact schema below.
            Previous sections context: {self._section_context}
            
            SECTION TEXT:
            {section_text}
            
            Return a JSON object with this exact structure:
            {{
                "section_type": "section",
                "number": "string (section number)",
                "title": "string (section title)",
                "content": "string (full section text)",
                "summary": "string (brief summary of purpose and impact)",
                "key_points": ["list of key points"],
                "defined_terms": {{"term": "definition"}} (optional),
                "impacts": [
                    {{
                        "sector": "string (affected sector)",
                        "impact_level": "integer 1-5 (1=minimal, 5=major)",
                        "description": "string (detailed impact description)",
                        "estimated_cost": "string (optional, e.g. '$1 billion')",
                        "timeline": "string (e.g. 'Effective from 2024', 'Phased over 5 years')",
                        "affected_groups": ["list of affected stakeholders"]
                    }}
                ],
                "referenced_sections": ["list of referenced section numbers"] (optional),
                "funding_amounts": {{"purpose": "amount as number or description"}} (optional)
            }}
            
            IMPORTANT:
            1. All fields are required unless marked (optional)
            2. For impact_level, use 1-5 scale where:
               1 = Minimal impact
               2 = Minor impact
               3 = Moderate impact
               4 = Significant impact
               5 = Major impact
            3. Timeline must specify when provisions take effect
            4. Affected_groups should list specific stakeholders
            5. For funding_amounts, use either numeric values (e.g., 500000000) or descriptive text (e.g., "15% of adjusted income")
            
            Return ONLY the JSON object, no additional text or explanations."""
            
            try:
                response = await self.agent.run(prompt)
                fixed_json = self._fix_json_response(response.data)
                result = BillSection.model_validate_json(fixed_json)
                
                # Update context for next sections
                self._section_context += f"\nSection {result.number}: {result.summary}"
                return result
            except Exception as e:
                print(f"Error analyzing section: {str(e)}")
                raise

    def _fix_json_response(self, response: str) -> str:
        """Fix common JSON formatting issues in the response"""
        # Remove any text before the first {
        response = response[response.find("{"):]
        # Remove any text after the last }
        response = response[:response.rfind("}") + 1]
        
        # Fix missing quotes around property names
        response = re.sub(r'(\s*?)(\w+)(:)', r'\1"\2"\3', response)
        
        # Fix trailing commas
        response = re.sub(r',(\s*?[}\]])', r'\1', response)
        
        # Fix missing commas
        response = re.sub(r'(["\d])\s*\n\s*"', r'\1,\n"', response)
        
        return response