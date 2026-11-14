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


class ExtractionCreateRequest(BaseModel):
    evidence_ids: List[str] = Field(..., min_length=1, max_length=10)
    expected_version: Optional[int] = None


class ReviewItemTerms(BaseModel):
    kind: str = Field(..., description="kind: refund, replacement, service, other")
    description: str = Field(..., min_length=1, max_length=2000)
    amount_minor: Optional[int] = None
    currency: Optional[str] = None
    due_at: Optional[str] = None

    @field_validator("kind")
    @classmethod
    def validate_kind(cls, v: str) -> str:
        if v not in {"refund", "replacement", "service", "other"}:
            raise ValueError("kind must be one of: refund, replacement, service, other")
        return v

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and len(v.strip()) != 3:
            raise ValueError("currency must be a 3-letter ISO code or null")
        return v.upper() if v else None


class ReviewItem(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    action: str = Field(..., description="'new' or 'revision'")
    supersedes_id: Optional[str] = None
    terms: ReviewItemTerms
    evidence_ids: List[str] = Field(..., min_length=1, max_length=10)

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        if v not in {"new", "revision"}:
            raise ValueError("action must be 'new' or 'revision'")
        return v


class ExtractionReviewRequest(BaseModel):
    expected_version: Optional[int] = None
    decision: str = Field(..., description="'approve' or 'reject'")
    items: List[ReviewItem] = []

    @field_validator("decision")
    @classmethod
    def validate_decision(cls, v: str) -> str:
        if v not in {"approve", "reject"}:
            raise ValueError("decision must be 'approve' or 'reject'")
        return v


class ExtractionCreateResponse(BaseModel):
    extraction: ExtractionSchema
    case_version: int


class ExtractionReviewResponse(BaseModel):
    extraction: ExtractionSchema
    commitments: List[CommitmentSchema] = []
    case_version: int


class CaseDetailResponse(BaseModel):
    case: CaseSchema
    evidence: List[EvidenceSchema] = []
    commitments: List[CommitmentSchema] = []
    extractions: List[ExtractionSchema] = []


class CaseCreateResponse(BaseModel):
    case: CaseSchema


class CaseListResponse(BaseModel):
    cases: List[CaseSchema]


class EvidenceUploadResponse(BaseModel):
    evidence: EvidenceSchema
    case_version: int


class EvidenceListResponse(BaseModel):
    evidence: List[EvidenceSchema]


class TimelineEventSchema(BaseModel):
    id: str
    case_id: str
    event_type: str
    description: str
    event_date: str
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TimelineResponse(BaseModel):
    timeline_events: List[TimelineEventSchema]


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    message: str


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: List[ErrorDetail] = []
    request_id: str


class ErrorResponse(BaseModel):
    error: ErrorPayload
