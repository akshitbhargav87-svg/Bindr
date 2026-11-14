from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class CaseCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    merchant_name: str = Field(..., min_length=1, max_length=200)


class CaseSchema(BaseModel):
    id: str
    title: str
    merchant_name: str
    status: str
    version: int
    resolution_note: Optional[str] = None
    resolved_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class EvidenceSchema(BaseModel):
    id: str
    case_id: str
    filename: str
    media_type: str
    size_bytes: int
    sha256: str
    created_at: str
    download_path: str

    model_config = ConfigDict(from_attributes=True)


class CommitmentCreateRequest(BaseModel):
    kind: str = Field("refund", description="Kind of commitment: refund, replacement, service, other")
    description: str = Field(..., min_length=1, max_length=2000)
    amount_minor: Optional[int] = None
    currency: Optional[str] = None
    due_at: Optional[str] = None
    status: str = Field("active", description="Status: active, superseded, fulfilled")
    supersedes_id: Optional[str] = None
    evidence_ids: List[str] = []

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in {"refund", "replacement", "service", "other"}:
            raise ValueError("kind must be one of: refund, replacement, service, other")
        return v

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        if v not in {"active", "superseded", "fulfilled"}:
            raise ValueError("status must be one of: active, superseded, fulfilled")
        return v


class CommitmentReviseRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    kind: Optional[str] = None
    amount_minor: Optional[int] = None
    currency: Optional[str] = None
    due_at: Optional[str] = None
    evidence_ids: List[str] = []


class CommitmentSchema(BaseModel):
    id: str
    case_id: str
    extraction_id: Optional[str] = None
    candidate_id: Optional[str] = None
    kind: str
    description: str
    amount_minor: Optional[int] = None
    currency: Optional[str] = None
    due_at: Optional[str] = None
    status: str
    supersedes_id: Optional[str] = None
    evidence_ids: List[str] = []
    reviewed_at: Optional[str] = None
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class ExtractionSchema(BaseModel):
    id: str
    case_id: str
    evidence_ids: List[str] = []
    status: str = "pending_review"
    candidates: List[dict] = []
    reviewed_commitment_ids: List[str] = []
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class CaseDetailResponse(BaseModel):
    case: CaseSchema
    evidence: List[EvidenceSchema] = []
    commitments: List[CommitmentSchema] = []
    extractions: List[ExtractionSchema] = []


class CaseCreateResponse(BaseModel):
    case: CaseSchema


class CaseListResponse(BaseModel):
    cases: List[CaseSchema]
