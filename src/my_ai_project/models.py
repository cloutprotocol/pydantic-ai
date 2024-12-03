from typing import List, Dict, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum

class SectionType(str, Enum):
    TITLE = "title"
    SUBTITLE = "subtitle"
    CHAPTER = "chapter"
    SUBCHAPTER = "subchapter"
    PART = "part"
    SECTION = "section"

class LegislativeImpact(BaseModel):
    sector: str
    impact_level: int = Field(..., ge=1, le=5)
    description: str
    estimated_cost: Optional[str] = None
    timeline: str
    affected_groups: List[str]

class BillSection(BaseModel):
    section_type: SectionType = Field(default=SectionType.SECTION)
    number: str
    title: str
    content: str
    summary: str = Field(..., description="Brief summary of the section's purpose and impact")
    key_points: List[str]
    defined_terms: Dict[str, str] = Field(..., description="Important terms defined in this section")
    impacts: List[LegislativeImpact]
    referenced_sections: List[str] = Field(..., description="Other sections referenced by this section")
    funding_amounts: Optional[Dict[str, Union[float, str]]] = Field(None, description="Funding allocations in USD or descriptive amounts")

class Citation(BaseModel):
    title: str
    section: str
    description: str
    url: Optional[HttpUrl]

class Amendment(BaseModel):
    original_text: str
    amended_text: str
    explanation: str
    effective_date: str
    impact_summary: str

class BillAnalysis(BaseModel):
    title: str
    bill_number: str
    congress_session: str
    introduction_date: datetime
    summary: str = Field(..., description="Executive summary of the entire bill")
    major_provisions: List[str]
    sections: List[BillSection]
    total_cost_estimate: str
    implementation_timeline: Dict[str, str]
    key_stakeholders: List[str]
    citations: List[Citation]
    amendments: List[Amendment]
    controversies: List[str] = Field(..., description="Potential controversial aspects")
    
class SearchResult(BaseModel):
    section: BillSection
    relevance_score: float = Field(..., ge=0, le=1)
    context: str
    highlights: List[str] 