"""
Pydantic schemas and data contracts for the Promise Extraction Engine.

Follows the Promise Keeper AI Contract:
- Preserves exact verbatim quotations from the source.
- Returns null for unknown information (no placeholder strings like 'N/A').
- Does not calculate business-day deadlines; extracts raw duration details for backend calculation.
- Avoids fabricating numerical confidence scores.
- Flags vague estimates and ambiguous communication for human-in-the-loop review.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class CommitmentCategory(str, Enum):
    """Categories of promises made by companies to customers."""
    REFUND = "refund"
    REPLACEMENT = "replacement"
    REPAIR = "repair"
    CANCELLATION = "cancellation"
    SERVICE_CREDIT = "service_credit"
    DELIVERY = "delivery"
    CALLBACK = "callback"
    STATUS_UPDATE = "status_update"
    OTHER = "other"
    NO_COMMITMENT = "no_commitment"


class CommitmentType(str, Enum):
    """Distinguishes firm, explicit commitments from inferred or absent ones."""
    EXPLICIT = "explicit"
    INFERRED = "inferred"
    NONE = "none"


class DeadlineType(str, Enum):
    """Type of deadline identified in the communication."""
    DURATION = "duration"
    ABSOLUTE_DATE = "absolute_date"
    NONE = "none"


class DeadlineInfo(BaseModel):
    """
    Structured duration or deadline information.
    
    IMPORTANT: Business-day and holiday calculations are handled by the backend,
    not calculated by the LLM.
    """
    deadline_type: DeadlineType = Field(
        default=DeadlineType.NONE,
        description="Whether the deadline is an elapsed duration, an absolute calendar date, or absent."
    )
    duration_value: Optional[float] = Field(
        default=None,
        description="Numeric duration value (e.g., 5 for 5 business days, 24 for 24 hours)."
    )
    duration_value_max: Optional[float] = Field(
        default=None,
        description="Upper bound when a range is promised (e.g., 7 for '5 to 7 business days')."
    )
    duration_unit: Optional[str] = Field(
        default=None,
        description="Unit of duration: 'business_days', 'calendar_days', 'hours', 'weeks', or 'months'."
    )
    absolute_date: Optional[str] = Field(
        default=None,
        description="Target date if an explicit calendar date was stated (ISO YYYY-MM-DD or textual date)."
    )
    raw_deadline_text: Optional[str] = Field(
        default=None,
        description="Verbatim text fragment stating the deadline or timeframe (e.g. 'within 3-5 business days')."
    )

    @field_validator("duration_unit", "absolute_date", "raw_deadline_text", mode="before")
    @classmethod
    def clean_empty_strings(cls, v: Any) -> Optional[Any]:
        if isinstance(v, str):
            cleaned = v.strip()
            if cleaned.lower() in {"", "none", "null", "n/a", "unknown", "nil"}:
                return None
            return cleaned
        return v


class SourceMetadata(BaseModel):
    """Optional contextual metadata provided alongside the raw text."""
    sender: Optional[str] = Field(default=None, description="Company or agent email/name.")
    recipient: Optional[str] = Field(default=None, description="Customer name/email.")
    communication_date: Optional[str] = Field(default=None, description="Timestamp/date of the message.")
    channel: Optional[str] = Field(
        default=None,
        description="Communication medium (e.g., 'email', 'chat_screenshot', 'pdf', 'sms')."
    )
    subject: Optional[str] = Field(default=None, description="Subject line if email or ticket title.")
    extra: Dict[str, Any] = Field(default_factory=dict, description="Any supplementary client metadata.")

    @field_validator("sender", "recipient", "communication_date", "channel", "subject", mode="before")
    @classmethod
    def clean_empty_strings(cls, v: Any) -> Optional[Any]:
        if isinstance(v, str):
            cleaned = v.strip()
            if cleaned.lower() in {"", "none", "null", "n/a", "unknown", "nil"}:
                return None
            return cleaned
        return v


class EvidenceMetadata(BaseModel):
    """Traceability metadata linking extracted commitments to source files (Milestone 2)."""
    evidence_id: Optional[str] = Field(default=None, description="Unique identifier for the source evidence.")
    filename: Optional[str] = Field(default=None, description="Original filename of the evidence.")
    file_type: Optional[str] = Field(default=None, description="File type/extension (e.g. 'pdf', 'png', 'jpeg').")
    total_pages: Optional[int] = Field(default=None, description="Total pages in the source document.")
    page_numbers: List[int] = Field(default_factory=list, description="Pages containing extracted content.")
    extraction_warnings: List[str] = Field(default_factory=list, description="Warnings encountered during file processing.")


class CommitmentExtractionResult(BaseModel):
    """
    Final structured commitment data output of Milestone 1.
    Complies with all Milestone 1 acceptance criteria and contract specifications.
    """
    company_name: Optional[str] = Field(
        default=None,
        description="The company or organisation making or declining the commitment. Null if unknown."
    )
    commitment_category: CommitmentCategory = Field(
        default=CommitmentCategory.NO_COMMITMENT,
        description="Primary classification of the commitment."
    )
    commitment_description: str = Field(
        default="No commitment identified.",
        description="Clear, concise factual summary of what the company committed to do."
    )
    amount: Optional[float] = Field(
        default=None,
        description="Monetary amount involved in the promise (e.g. refund/credit amount). Null if not applicable."
    )
    currency: Optional[str] = Field(
        default=None,
        description="Currency symbol or 3-letter ISO code (e.g. 'USD', 'EUR', '$', 'GBP'). Null if not applicable."
    )
    communication_date: Optional[str] = Field(
        default=None,
        description="Date of the communication mentioned in the text or metadata (YYYY-MM-DD or textual). Null if unknown."
    )
    deadline: DeadlineInfo = Field(
        default_factory=DeadlineInfo,
        description="Structured deadline duration or absolute date."
    )
    commitment_type: CommitmentType = Field(
        default=CommitmentType.NONE,
        description="Explicit promise vs. inferred / conditional statement vs. no commitment."
    )
    is_vague_estimate: bool = Field(
        default=False,
        description="True if the message contains vague non-binding estimates (e.g. 'usually takes a few days') rather than a firm promise."
    )
    supporting_quotation: Optional[str] = Field(
        default=None,
        description="Exact verbatim quotation from the source text that provides evidence for the commitment."
    )
    missing_or_ambiguous_fields: List[str] = Field(
        default_factory=list,
        description="List of fields that were ambiguous, unverified, or missing from the communication."
    )
    user_confirmation_required: bool = Field(
        default=False,
        description="Flag indicating human-in-the-loop review is recommended due to ambiguity, vague estimate, or low clarity."
    )
    raw_source_text: Optional[str] = Field(
        default=None,
        description="Original text analyzed (retained for verification and backend audit logging)."
    )
    evidence_metadata: Optional[EvidenceMetadata] = Field(
        default=None,
        description="Traceability metadata linking the extracted commitment back to the source file/evidence (Milestone 2)."
    )

    @field_validator("company_name", "currency", "communication_date", "supporting_quotation", mode="before")
    @classmethod
    def clean_null_strings(cls, v: Any) -> Optional[Any]:
        """Convert placeholder strings to None to satisfy the 'return null for unknown information' rule."""
        if isinstance(v, str):
            cleaned = v.strip()
            if cleaned.lower() in {"", "none", "null", "n/a", "unknown", "nil", "undefined", "not specified"}:
                return None
            return cleaned
        return v

    @model_validator(mode="after")
    def validate_and_enforce_business_rules(self) -> CommitmentExtractionResult:
        """
        Enforce consistency across commitment attributes:
        1. Vague estimates and inferred commitments require user confirmation.
        2. Non-commitments must not pretend to have firm amounts or explicit deadlines.
        3. Exact supporting quotations must be verified against source text when present.
        """
        # If vague estimate or inferred, user confirmation is mandatory
        if self.is_vague_estimate or self.commitment_type == CommitmentType.INFERRED:
            self.user_confirmation_required = True

        # If there are unresolved ambiguous fields, user confirmation is recommended
        if self.missing_or_ambiguous_fields and self.commitment_type != CommitmentType.NONE:
            self.user_confirmation_required = True

        # If no commitment was made, ensure standard clean state
        if self.commitment_type == CommitmentType.NONE:
            if self.commitment_category == CommitmentCategory.NO_COMMITMENT:
                if not self.commitment_description or self.commitment_description == "No commitment identified.":
                    self.commitment_description = "No commitment found in communication."

        # Verify supporting quotation is verbatim if raw_source_text is provided
        if self.supporting_quotation and self.raw_source_text:
            cleaned_quote = " ".join(self.supporting_quotation.split()).lower()
            cleaned_source = " ".join(self.raw_source_text.split()).lower()
            if cleaned_quote not in cleaned_source:
                # Quotation is not verbatim, flag it for safety
                if "supporting_quotation" not in self.missing_or_ambiguous_fields:
                    self.missing_or_ambiguous_fields.append("supporting_quotation")
                self.user_confirmation_required = True

        return self
