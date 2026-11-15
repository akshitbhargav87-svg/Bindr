"""Concrete A1 request schemas for the frozen v2 route families."""

import re
from datetime import date as Date, time as Time
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from pydantic import BaseModel, ConfigDict, Field, model_validator, field_validator


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Communication(Strict):
    date: Date | None = None
    time: Time | None = None
    timezone: str = "Asia/Kolkata"
    precision: Literal["unknown", "date", "timestamp"] = "unknown"
    provenance: Literal["user_confirmed", "message_metadata", "extracted"] = (
        "user_confirmed"
    )
    original_wording: str | None = Field(None, max_length=2000)

    @field_validator("date", mode="before")
    @classmethod
    def iso_date(cls, value):
        if value is not None and not (
            type(value) is Date
            or isinstance(value, str)
            and re.fullmatch(r"\d{4}-\d{2}-\d{2}", value)
        ):
            raise ValueError("Date must be YYYY-MM-DD")
        return value

    @field_validator("time", mode="before")
    @classmethod
    def local_time(cls, value):
        if value is not None and not (
            type(value) is Time
            and value.tzinfo is None
            or isinstance(value, str)
            and re.fullmatch(r"\d{2}:\d{2}:\d{2}", value)
        ):
            raise ValueError("Time must be local HH:mm:ss; timezone is separate")
        return value

    @field_validator("timezone")
    @classmethod
    def known_zone(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("Unknown IANA timezone")
        return value

    @model_validator(mode="after")
    def precision_matches(self):
        if self.precision == "unknown" and (
            self.date is not None or self.time is not None
        ):
            raise ValueError("Unknown precision requires null date/time")
        if self.precision == "date" and (self.date is None or self.time is not None):
            raise ValueError("Date precision requires date only")
        if self.precision == "timestamp" and (self.date is None or self.time is None):
            raise ValueError("Timestamp precision requires date and time")
        return self


class Capture(Strict):
    text: str = Field("", max_length=50000)
    communication: Communication = Field(default_factory=Communication)
    evidence_ids: list[str] = Field(default_factory=list, max_length=10)


class DraftCreate(Strict):
    capture: Capture


class DraftUpdate(DraftCreate):
    expected_version: int = Field(ge=1, strict=True)


class CaseCreate(Strict):
    title: str = Field(min_length=1, max_length=200)
    merchant_name: str = Field(min_length=1, max_length=200)

    @field_validator("title", "merchant_name")
    @classmethod
    def trim(cls, value):
        if not value.strip():
            raise ValueError("Must not be blank")
        return value.strip()
