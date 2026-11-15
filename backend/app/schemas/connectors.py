from typing import Literal
from pydantic import Field, field_validator
from backend.app.schemas.platform import Strict
from backend.app.schemas.workflow import Versioned


class ReviewedSend(Versioned):
    recipient: str = Field(
        min_length=3, max_length=320, pattern=r"^[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+$"
    )
    subject: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=20000)
    source_ids: list[str] = Field(default_factory=list, max_length=10)
    receive_replies: bool = False
    reviewed: Literal[True]

    @field_validator("recipient", "subject")
    @classmethod
    def no_header_injection(cls, value):
        if "\r" in value or "\n" in value:
            raise ValueError("Header line breaks are forbidden")
        return value


class GmailImport(Strict):
    message_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,200}$")
    alias_token: str = Field(min_length=20, max_length=200)
