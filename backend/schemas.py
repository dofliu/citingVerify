from pydantic import BaseModel
from typing import Optional, List

class PaperBase(BaseModel):
    title: str
    abstract: Optional[str] = None

class PaperCreate(PaperBase):
    pass

class Paper(PaperBase):
    id: int

    class Config:
        orm_mode = True

class Reference(BaseModel):
    raw_text: str
    status: str = "Unprocessed" # e.g., "Verified", "Not Found", "Format Error"
    authors: Optional[List[str]] = None
    year: Optional[int] = None
    title: Optional[str] = None
    source: Optional[str] = None
    verified_doi: Optional[str] = None
    verification_score: float = 0.0
    format_suggestion: Optional[str] = None
    source_url: Optional[str] = None

class Summary(BaseModel):
    total_references: int
    verified_count: int
    not_found_count: int
    format_error_count: int

class UploadResponse(BaseModel):
    filename: str
    summary: Summary
    references: List[Reference]
