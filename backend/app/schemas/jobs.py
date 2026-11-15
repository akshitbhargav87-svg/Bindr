from typing import Literal
from pydantic import Field, model_validator
from backend.app.schemas.platform import Strict
from backend.app.schemas.workflow import Versioned


class Notifications(Strict):
    expected_version: int = Field(ge=0, strict=True)
    in_app: bool = True
    email: bool = False
    push: bool = False
    whatsapp: bool = False
    days_before: list[int] = Field(
        default_factory=lambda: [3, 1, 0], min_length=1, max_length=10
    )

    @model_validator(mode="after")
    def reminder_offsets(self):
        if len(set(self.days_before)) != len(self.days_before) or any(
            type(d) is not int or not 0 <= d <= 30 for d in self.days_before
        ):
            raise ValueError("Reminder offsets must be unique integers from 0 to 30")
        return self

    follow_up_days: int | None = Field(None, ge=1, le=90, strict=True)


class ExportRequest(Versioned):
    obligation_ids: list[str] | None = Field(None, max_length=30)
    include_history: bool = True
    trusted_timestamp: bool = False
    source_ids: list[str] = Field(default_factory=list, max_length=30)
    reviewed_wording: str = Field("", max_length=20000)
    formats: list[Literal["pdf", "bundle", "data"]] = Field(min_length=1, max_length=3)

    @model_validator(mode="after")
    def unique(self):
        if self.obligation_ids is not None:
            if len(set(self.obligation_ids)) != len(self.obligation_ids):
                raise ValueError("Duplicate obligation selection")
            if self.include_history:
                raise ValueError(
                    "Selected-fact export requires include_history:false to avoid exposing other history"
                )
        if self.trusted_timestamp and "bundle" not in self.formats:
            raise ValueError("A timestamp receipt requires bundle format")
        if len(set(self.source_ids)) != len(self.source_ids) or len(
            set(self.formats)
        ) != len(self.formats):
            raise ValueError("Duplicate selection")
        return self


class DeleteCase(Versioned):
    confirmation: Literal["DELETE"]


class DeleteAccount(Strict):
    confirmation: Literal["DELETE MY ACCOUNT"]
