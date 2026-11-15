from datetime import datetime, date, time as LocalTime
from typing import Literal
from pydantic import Field, field_validator, model_validator
from backend.app.schemas.platform import Strict, Communication


class Terms(Strict):
    kind: Literal["refund", "replacement", "repair", "delivery", "service", "other"]
    description: str = Field(min_length=1, max_length=4000)
    amount_minor: int | None = Field(None, ge=0, le=10**12, strict=True)
    currency: str | None = Field(None, pattern=r"^[A-Z]{3}$")
    due_at: datetime | None = None

    @field_validator("currency")
    @classmethod
    def supported_currency(cls, value):
        if value is not None and value not in {
            "INR",
            "USD",
            "EUR",
            "GBP",
            "JPY",
            "AUD",
            "CAD",
            "SGD",
        }:
            raise ValueError(
                "Unsupported currency; supported ISO currencies: INR/USD/EUR/GBP/JPY/AUD/CAD/SGD"
            )
        return value

    @field_validator("due_at", mode="before")
    @classmethod
    def iso_instant(cls, value):
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("due_at must be an ISO timestamp with offset")
        return value

    @model_validator(mode="after")
    def consistency(self):
        if (self.amount_minor is None) != (self.currency is None):
            raise ValueError("Amount and currency must both be set or both null")
        if not self.description.strip():
            raise ValueError("Description must not be blank")
        if self.due_at is not None and self.due_at.utcoffset() is None:
            raise ValueError("due_at requires an explicit timezone offset")
        return self


class Source(Strict):
    evidence_id: str = Field(min_length=1, max_length=36)
    quote: str = Field(min_length=1, max_length=10000)
    page: int | None = Field(None, ge=1, strict=True)
    message_id: str | None = Field(None, max_length=200)
    start_seconds: float | None = Field(None, ge=0, allow_inf_nan=False)
    end_seconds: float | None = Field(None, ge=0, allow_inf_nan=False)

    @model_validator(mode="after")
    def segment(self):
        if (self.start_seconds is None) != (self.end_seconds is None):
            raise ValueError("Both audio offsets are required")
        if self.start_seconds is not None and self.end_seconds <= self.start_seconds:
            raise ValueError("Invalid audio segment")
        return self


class Versioned(Strict):
    expected_version: int = Field(ge=1, strict=True)


class ManualPromise(Versioned):
    terms: Terms
    origin: Literal["user_attested", "source_backed"]
    sources: list[Source] = Field(default_factory=list, max_length=10)
    confirmed: Literal[True]
    predecessor_id: str | None = None
    reason: str | None = Field(None, max_length=2000)
    deadline: "DeadlinePreview | None" = None
    deadline_override_reason: str | None = Field(None, max_length=2000)

    @model_validator(mode="after")
    def honest_origin(self):
        if (self.origin == "source_backed") != bool(self.sources):
            raise ValueError(
                "Source-backed input requires sources; user attestation does not fabricate sources"
            )
        if self.predecessor_id and not self.reason:
            raise ValueError("Revision requires a reason")
        return self


class Allocation(Strict):
    obligation_id: str
    amount_minor: int | None = Field(None, ge=1, le=10**12, strict=True)


class Outcome(Versioned):
    kind: Literal["partial", "full", "pending", "company_claim", "correction"]
    allocations: list[Allocation] = Field(default_factory=list, max_length=30)
    received_at: datetime | None = None
    note: str = Field("", max_length=4000)
    source_ids: list[str] = Field(default_factory=list, max_length=10)
    corrects_event_id: str | None = None

    @model_validator(mode="after")
    def valid_event(self):
        if self.kind == "correction":
            if not self.corrects_event_id or self.allocations:
                raise ValueError(
                    "Correction must reference an event without new allocations"
                )
        elif not self.allocations or self.corrects_event_id:
            raise ValueError("An outcome requires allocations")
        if len({a.obligation_id for a in self.allocations}) != len(self.allocations):
            raise ValueError("Duplicate allocation")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Duplicate evidence IDs")
        if self.kind in ("partial", "full") and self.received_at is None:
            raise ValueError("Receipt time is required")
        if self.received_at and self.received_at.utcoffset() is None:
            raise ValueError("Receipt time requires timezone")
        return self


class Lifecycle(Versioned):
    action: Literal["reopen", "archive", "restore", "edit_identity"]
    reason: str = Field(min_length=1, max_length=2000)
    title: str | None = Field(None, min_length=1, max_length=200)
    merchant_name: str | None = Field(None, min_length=1, max_length=200)


class DeadlinePreview(Strict):
    anchor: Communication
    anchor_confirmed: bool
    condition_fulfilled: bool | None = None
    conditional: bool = False
    expression: str = Field("", max_length=2000)
    unit: Literal["calendar_days", "business_days", "explicit_date"]
    minimum: int = Field(0, ge=0, le=3660, strict=True)
    maximum: int = Field(0, ge=0, le=3660, strict=True)
    explicit_date: date | None = None
    explicit_time: LocalTime | None = None
    calendar_id: Literal["weekend_only", "custom"] = "weekend_only"
    calendar_version: str = Field("1", min_length=1, max_length=80)
    weekends: list[int] = Field(default_factory=lambda: [5, 6], max_length=6)
    holidays: list[date] = Field(default_factory=list, max_length=1000)

    @field_validator("explicit_time", mode="before")
    @classmethod
    def strict_time(cls, value):
        return Communication.local_time(value)

    @model_validator(mode="after")
    def range_check(self):
        if self.maximum < self.minimum:
            raise ValueError("Maximum must be >= minimum")
        if len(set(self.weekends)) != len(self.weekends) or any(
            d < 0 or d > 6 for d in self.weekends
        ):
            raise ValueError("Invalid weekdays")
        if self.calendar_id == "weekend_only" and (
            self.holidays or self.weekends != [5, 6] or self.calendar_version != "1"
        ):
            raise ValueError(
                "Weekend-only calendar is fixed; use custom for user-supplied assumptions"
            )
        if self.unit == "explicit_date" and self.explicit_date is None:
            raise ValueError("Explicit date is required")
        return self


class ExtractionRequest(Versioned):
    evidence_ids: list[str] = Field(min_length=1, max_length=10)
    metadata_references: dict[str, Communication] = Field(default_factory=dict)

    @model_validator(mode="after")
    def unique(self):
        if len(set(self.evidence_ids)) != len(self.evidence_ids):
            raise ValueError("Duplicate evidence IDs")
        if set(self.metadata_references) - set(self.evidence_ids):
            raise ValueError("Metadata must reference selected evidence")
        return self


class Temporal(Strict):
    original_wording: str | None = Field(None, max_length=4000)
    anchor: Communication | None = None
    duration: dict | None = None
    range: dict | None = None
    parse_status: Literal["parsed", "unknown", "invalid", "conditional"]


class Relation(Strict):
    kind: Literal[
        "new", "corroboration", "revision", "contradiction", "cancellation", "uncertain"
    ]
    predecessor_id: str | None = None
    explanation: str = Field("", max_length=4000)


class Condition(Strict):
    text: str | None = Field(None, max_length=4000)
    fulfilled: bool | None = None


class Candidate(Strict):
    candidate_id: str = Field(min_length=1, max_length=80)
    terms: Terms
    sources: list[Source] = Field(min_length=1, max_length=10)
    temporal: Temporal
    relation: Relation
    condition: Condition
    warnings: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def invalid_date_stays_null(self):
        if self.temporal.parse_status == "invalid" and (
            self.terms.due_at is not None or not self.warnings
        ):
            raise ValueError(
                "Invalid source dates require a null proposed due_at and visible warning"
            )
        return self


class ProposalResult(Strict):
    schema_version: Literal[2]
    proposal_id: str = Field(min_length=1, max_length=80)
    candidates: list[Candidate] = Field(max_length=30)
    document_warnings: list[str] = Field(default_factory=list, max_length=30)

    @model_validator(mode="after")
    def unique_candidates(self):
        if len({c.candidate_id for c in self.candidates}) != len(self.candidates):
            raise ValueError("Duplicate candidate IDs")
        return self


class Decision(Strict):
    candidate_id: str
    action: Literal["confirm", "reject", "corroborate", "cancel"]
    edited_terms: Terms | None = None
    predecessor_id: str | None = None
    deadline_override_reason: str | None = Field(None, max_length=2000)
    deadline: DeadlinePreview | None = None


class Review(Versioned):
    proposal_id: str
    decisions: list[Decision] = Field(min_length=1, max_length=30)

    @model_validator(mode="after")
    def unique(self):
        if len({d.candidate_id for d in self.decisions}) != len(self.decisions):
            raise ValueError("Duplicate candidate decision")
        return self


class CommunicationCorrection(Versioned):
    communication: Communication
    reason: str = Field(min_length=1, max_length=2000)


class Note(Versioned):
    text: str = Field(min_length=1, max_length=4000)
    origin: Literal["user_note", "phone_note"]
    occurred_at: datetime | None = None
    source_ids: list[str] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def aware_time(self):
        if self.occurred_at and self.occurred_at.utcoffset() is None:
            raise ValueError("Note time requires an explicit timezone offset")
        if len(set(self.source_ids)) != len(self.source_ids):
            raise ValueError("Duplicate source IDs")
        return self


ManualPromise.model_rebuild()
