"""Track B's explicit v2 proposal seam; no implicit v1 field changes."""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictData(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Communication(StrictData):
    date: str | None = None
    time: str | None = None
    timezone: str = "Asia/Kolkata"
    precision: Literal["unknown", "date", "timestamp"] = "unknown"
    provenance: Literal["user_confirmed", "message_metadata", "extracted"] = "extracted"
    original_wording: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def calendar(self):
        ZoneInfo(self.timezone)
        if self.date is not None:
            if date.fromisoformat(self.date).isoformat() != self.date:
                raise ValueError("Use an exact YYYY-MM-DD date.")
        if self.time is not None:
            datetime.strptime(self.time, "%H:%M:%S")
        if self.precision != "unknown" and self.date is None:
            raise ValueError("A dated source requires its communication date.")
        if self.precision == "timestamp" and self.time is None:
            raise ValueError("A timestamp requires its communication time.")
        return self


class Segment(StrictData):
    text: str = Field(min_length=1, max_length=50000)
    page: int | None = Field(default=None, ge=1, le=50)
    message_id: str | None = Field(default=None, max_length=200)
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def offsets(self):
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError("Audio references require both offsets.")
        if self.start_ms is not None and self.end_ms <= self.start_ms:
            raise ValueError("Audio offsets must be ordered.")
        return self


class Source(StrictData):
    evidence_id: str = Field(min_length=1, max_length=200)
    segments: list[Segment] = Field(min_length=1, max_length=100)
    communication: Communication = Field(default_factory=Communication)


class ProposalRequest(StrictData):
    schema_version: Literal[2] = 2
    case_id: str = Field(min_length=1, max_length=200)
    request_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,100}$")
    evidence: list[Source] = Field(min_length=1, max_length=10)
    existing_obligations: list[dict] = Field(default_factory=list, max_length=100)
    timeout_seconds: int = Field(default=30, ge=1, le=90)

    @model_validator(mode="after")
    def bounds(self):
        import json
        ids = [e.evidence_id for e in self.evidence]
        if len(set(ids)) != len(ids):
            raise ValueError("Evidence IDs must be unique.")
        if sum(len(s.text) for e in self.evidence for s in e.segments) > 50000:
            raise ValueError("Evidence exceeds 50,000 characters; split the intake explicitly.")
        if len(json.dumps(self.existing_obligations, ensure_ascii=False)) > 50000:
            raise ValueError("Existing-obligation context exceeds its explicit 50,000-character bound.")
        old_ids=[]
        for obligation in self.existing_obligations:
            if not isinstance(obligation.get('id'), str) or obligation.get('case_id',self.case_id)!=self.case_id:
                raise ValueError("Existing obligations must belong to this authorized case snapshot.")
            old_ids.append(obligation['id'])
            if obligation.get('communication'):
                Communication.model_validate(obligation['communication'])
        if len(old_ids)!=len(set(old_ids)):
            raise ValueError("Existing obligation IDs must be unique.")
        return self


class Terms(StrictData):
    kind: Literal["refund", "replacement", "service", "other"]
    description: str = Field(min_length=1, max_length=2000)
    amount_minor: int | None
    currency: str | None
    due_at: str | None

    @model_validator(mode="after")
    def money_and_date(self):
        if not self.description.strip():
            raise ValueError("Description must be nonempty.")
        if (self.amount_minor is None) != (self.currency is None):
            raise ValueError("Amount and currency must be supplied together.")
        if self.amount_minor is not None and not 0 <= self.amount_minor <= 9007199254740991:
            raise ValueError("Amount must be nonnegative integer minor units.")
        if self.currency is not None:
            import re
            if not re.fullmatch(r"[A-Z]{3}", self.currency):
                raise ValueError("Use an ISO currency code.")
        if self.due_at is not None:
            instant = datetime.fromisoformat(self.due_at.replace("Z", "+00:00"))
            if instant.tzinfo is None:
                raise ValueError("Proposed instants require an explicit offset.")
        return self


class Citation(StrictData):
    evidence_id: str
    quote: str = Field(min_length=1, max_length=2000)
    page: int | None = None
    message_id: str | None = None
    start_ms: int | None = None
    end_ms: int | None = None

    @field_validator("quote")
    @classmethod
    def not_blank(cls, value):
        if not value.strip():
            raise ValueError("A source quote cannot be blank.")
        return value


class Temporal(StrictData):
    wording: str | None = Field(max_length=2000)
    anchor: str | None = Field(max_length=2000)
    duration: str | None = Field(max_length=2000)
    range: str | None = Field(max_length=2000)
    parse_status: Literal["explicit", "needs_calculation", "anchor_missing", "invalid", "ambiguous", "unknown"]


class Condition(StrictData):
    trigger: str | None = Field(max_length=2000)
    status: Literal["unknown", "confirmed", "not_applicable"]


class Relation(StrictData):
    kind: Literal["new", "corroboration", "revision", "contradiction", "cancellation", "uncertain"]
    predecessor_id: str | None
    explanation: str = Field(min_length=1, max_length=2000)


class Candidate(StrictData):
    candidate_id: str = Field(min_length=1, max_length=200)
    terms: Terms
    sources: list[Citation] = Field(min_length=1, max_length=10)
    temporal: Temporal
    relation: Relation
    condition: Condition
    warnings: list[str] = Field(max_length=30)

    @field_validator("warnings")
    @classmethod
    def warning_bounds(cls, warnings):
        if any(not 1 <= len(w) <= 500 for w in warnings):
            raise ValueError("Invalid warning length.")
        return warnings


class Proposal(StrictData):
    schema_version: Literal[2]
    proposal_id: str = Field(min_length=1, max_length=200)
    candidates: list[Candidate] = Field(max_length=50)
    document_warnings: list[str] = Field(max_length=30)
