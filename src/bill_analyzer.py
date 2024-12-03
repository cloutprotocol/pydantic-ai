from typing import List, Dict, Optional, AsyncIterator, Any
from pydantic_ai import Agent
from pydantic import BaseModel, Field
import asyncio
from datetime import datetime
from src.models import BillAnalysis, BillSection, LegislativeImpact, Citation, Amendment
from dotenv import load_dotenv
import os

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
            system_prompt="""You are an expert legislative analyst specializing in 
            analyzing complex congressional bills. Focus on identifying key impacts,
            funding allocations, and cross-references between sections. 
            
            For each section, you must:
            1. Extract the section number and title
            2. Provide a clear summary
            3. Identify key points and defined terms
            4. List any funding amounts with their purposes
            5. Note cross-references to other sections
            6. Analyze potential impacts on different sectors
            
            Be precise with numbers and maintain context between sections."""
        )
        self.max_concurrent_tasks = max_concurrent_tasks
        self.cache_results = cache_results
        self._analysis_cache = {}
        self._task_queue = asyncio.Queue()
        self._section_context = {}

    async def add_section_for_analysis(
        self,
        section_text: str,
        context: Optional[Dict[str, Any]] = None,
        priority: int = 1
    ):
        """Add a section to the analysis queue"""
        task = AnalysisTask(
            section_text=section_text,
            context=context or {},
            priority=priority
        )
        await self._task_queue.put(task)

    async def analyze_sections(self) -> AsyncIterator[AnalysisResult]:
        """Process sections in parallel with controlled concurrency"""
        tasks = []
        while not self._task_queue.empty() or tasks:
            # Start new tasks up to max_concurrent_tasks
            while len(tasks) < self.max_concurrent_tasks and not self._task_queue.empty():
                task = await self._task_queue.get()
                analysis_task = self._analyze_section_task(task)
                tasks.append(asyncio.create_task(analysis_task))
            
            if not tasks:
                break
                
            # Wait for any task to complete
            done, pending = await asyncio.wait(
                tasks,
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Handle completed tasks
            for task in done:
                result = await task
                tasks = list(pending)
                yield result

    async def _analyze_section_task(self, task: AnalysisTask) -> AnalysisResult:
        """Analyze a single section with timing and metadata"""
        start_time = asyncio.get_event_loop().time()
        
        # Check cache if enabled
        cache_key = hash(task.section_text)
        if self.cache_results and cache_key in self._analysis_cache:
            return self._analysis_cache[cache_key]

        try:
            # Create analysis prompt with context
            prompt = f"""Analyze this bill section and return a structured analysis following the exact schema below.
            Previous sections context: {self._section_context}
            
            SECTION TEXT:
            {task.section_text}
            
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
                        "sector": "string",
                        "impact_level": "integer 1-5",
                        "description": "string",
                        "estimated_cost": "string (optional)",
                        "timeline": "string",
                        "affected_groups": ["list of groups"]
                    }}
                ],
                "referenced_sections": ["list of referenced section numbers"] (optional),
                "funding_amounts": {{"purpose": "amount as number or description"}} (optional)
            }}
            
            Ensure all required fields are present and properly formatted.
            For funding_amounts, you can use either numeric values (e.g., 500000000) or descriptive text (e.g., "15% of adjusted income").
            Be precise with numbers and maintain context between sections."""

            # Get analysis from agent
            response = await self.agent.run(prompt)
            
            # Parse response into BillSection
            section = BillSection.parse_raw(response.data)
            
            processing_time = asyncio.get_event_loop().time() - start_time
            
            result = AnalysisResult(
                section=section,
                confidence_score=0.95,  # This should be calculated based on model confidence
                analysis_metadata={
                    "model": "gpt-4",
                    "timestamp": datetime.utcnow().isoformat(),
                    "version": "1.0"
                },
                processing_time=processing_time
            )
            
            # Update context and cache
            self._section_context[section.number] = {
                "title": section.title,
                "summary": section.summary,
                "key_points": section.key_points
            }
            
            if self.cache_results:
                self._analysis_cache[cache_key] = result
                
            return result
            
        except Exception as e:
            # Log error and return partial analysis if possible
            print(f"Error analyzing section: {str(e)}")
            raise