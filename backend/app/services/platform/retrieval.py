"""Authorized snapshot boundary. Evidence is inert data, not executable tool instructions."""

from backend.app.services.platform.workflow import owned_case, snapshot, sources
from backend.app.services.storage import storage_service
from backend.app.services.case_state import fail


def retrieve(db, owner, case_id, current_version):
    case = owned_case(db, owner, case_id)
    if case.version != current_version:
        fail(409, "VERSION_CONFLICT", "Refresh the case before asking a question.")
    record = snapshot(db, case)
    from backend.app.models.evidence import Evidence
    from backend.app.ai.document_processor import DocumentProcessor

    evidence = (
        db.query(Evidence)
        .filter_by(case_id=case_id)
        .order_by(Evidence.id)
        .limit(30)
        .all()
    )
    citations = {}
    remaining = 50000
    for row in evidence:
        suffix = {
            "text/plain": ".txt",
            "image/png": ".png",
            "image/jpeg": ".jpg",
            "application/pdf": ".pdf",
        }.get(row.media_type)
        if not suffix:
            continue
        from backend.app.services.platform.media import original

        document = DocumentProcessor().process_bytes(original(row), "evidence" + suffix)
        for page in document.pages:
            if remaining <= 0:
                break
            value = page.text[:remaining]
            remaining -= len(value)
            key = f"{row.id}:page:{page.page_number}"
            citations[key] = {
                "citation_id": key,
                "evidence_id": row.id,
                "page": page.page_number,
                "text": value,
                "trust": "untrusted_company_source",
            }
    return {
        "case_id": case.id,
        "version": case.version,
        "facts": record,
        "sources": list(citations.values()),
        "truncated": remaining <= 0,
    }, citations


def validate_answer(answer, citations):
    from pydantic import BaseModel, ConfigDict, Field, model_validator
    from typing import Literal

    class Citation(BaseModel):
        model_config = ConfigDict(extra="forbid")
        citation_id: str
        quote: str = Field(min_length=1, max_length=4000)

    class Answer(BaseModel):
        model_config = ConfigDict(extra="forbid")
        status: Literal["answered", "insufficient_evidence"]
        answer: str = Field(max_length=12000)
        citations: list[Citation] = Field(max_length=30)

        @model_validator(mode="after")
        def grounded(self):
            if self.status == "answered" and not self.citations:
                raise ValueError("Answers require citations")
            for c in self.citations:
                if (
                    c.citation_id not in citations
                    or c.quote not in citations[c.citation_id]["text"]
                ):
                    raise ValueError("Invalid source citation")
            return self

    try:
        return Answer.model_validate(answer).model_dump()
    except Exception:
        fail(502, "AI_INVALID_OUTPUT", "Answer citations could not be verified.")
