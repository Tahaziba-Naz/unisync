from datetime import date
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

CATEGORIES = ("study_resource", "internship", "job", "hackathon", "scholarship", "notice", "event")

class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    quote: str = Field(min_length=1, max_length=500)

class RecordDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=4, max_length=500)
    category: Literal["study_resource", "internship", "job", "hackathon", "scholarship", "notice", "event"]
    source_url: str = Field(min_length=8, max_length=500)
    apply_url: str | None = Field(default=None, max_length=500)
    deadline: date | None = None
    eligibility: str | None = None
    description: str | None = None
    published_date: date | None = None
    evidence: list[Evidence] = Field(min_length=1)

class DiscoveryOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    records: list[RecordDraft]

class ReviewOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    verdict: Literal["ACCEPT", "REJECT", "FLAG"]
    reason: str = Field(min_length=1, max_length=2000)
    concerns: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    missing_or_suspicious: list[str] = Field(default_factory=list)
