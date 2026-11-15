"""Extractive case questions: no evidence tools, model instructions or cross-case retrieval."""
from __future__ import annotations
import re


def answer_case(snapshot, question, current_version):
    """A supplies an already authorized snapshot. Responses never authorize retrieval.

    Quotes are presented as attributed source statements, not verified company actions.
    Conservative lexical retrieval abstains when relevance cannot be established.
    """
    abstain = {"answer": None, "citations": [], "abstention": "Insufficient evidence in this case.",
               "version": snapshot.get("version")}
    if current_version != snapshot.get("version") or not isinstance(question, str) or not 1 <= len(question) <= 2000:
        return {**abstain, "abstention": "Reload the current case and review your question."}
    if re.search(r"other (?:account|case)|ignore .*instructions|system prompt|send |https?://", question, re.I):
        return abstain
    terms = {s.lower() for s in re.findall(r"\w{3,}", question)} - {"what", "they", "the", "did", "was", "this", "case", "promise", "promised"}
    changes = bool(re.search(r"chang|revis|difference", question, re.I))
    call = bool(re.search(r"call|audio|recording", question, re.I))
    hits = []
    for source in snapshot.get("sources", []):
        if source.get("case_id") != snapshot.get("id") or source.get("deleted") or source.get("revoked"):
            continue
        for segment in source.get("segments", []):
            text = segment.get("text", "")
            if not text or len(text) > 2000:
                continue
            if call and segment.get("start_ms") is None:
                continue
            if re.search(r"ignore .*instructions|system message|<script|exfiltrat", text, re.I):
                continue
            overlap = terms.intersection(re.findall(r"\w{3,}", text.lower()))
            if not overlap and not (changes and source.get("role") in {"original", "revision"}):
                continue
            hits.append((len(overlap), source, segment))
    hits.sort(key=lambda h: h[0], reverse=True)
    hits = hits[:4]
    if not hits or (changes and not {"original", "revision"}.issubset({s.get("role") for _, s, _ in hits})):
        return abstain
    citations = [{"evidence_id": s["evidence_id"], "quote": p["text"], "page": p.get("page"),
                  "message_id": p.get("message_id"), "start_ms": p.get("start_ms"), "end_ms": p.get("end_ms"),
                  "origin": s.get("origin", "company_statement")} for _, s, p in hits]
    return {"answer": "Relevant source statements are quoted below. Their contents are not independently verified.",
            "citations": citations, "abstention": None, "version": snapshot["version"]}


def confirmation_draft(note, company):
    if not isinstance(note, str) or not 1 <= len(note.strip()) <= 5000:
        raise ValueError("Review the phone note first.")
    if not isinstance(company, str) or not 1 <= len(company.strip()) <= 200:
        raise ValueError("Review the company name.")
    return {"subject": "Please confirm our conversation in writing",
            "body": f"Hello {company},\n\nMy note of our conversation is:\n{note}\n\nPlease confirm or correct the terms, amount and expected date in writing.\nThank you.",
            "origin": "user_note", "requires_review": True, "sent": False}
