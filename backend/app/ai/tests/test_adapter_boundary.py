"""Final extraction boundary checks, independent of network and provider credentials."""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from backend.app.services.ai_adapter import AIInvalidOutputError, validate_ai_extraction_output, _confirmed_deadline
from backend.app.ai.schemas import DeadlineInfo


def candidate():
    return {"schema_version": 1, "candidates": [{
        "candidate_id": "c1", "terms": {"kind": "refund", "description": "Refund", "amount_minor": 499900, "currency": "INR", "due_at": None},
        "sources": [{"evidence_id": "e1", "quote": "Refund INR 4999"}], "confidence": 0.0,
        "warnings": [], "revision": {"relation": "new", "supersedes_id": None, "reason": "New promise"}}]}


@pytest.mark.parametrize("variant", ["extra_candidate", "extra_terms", "missing_nullable", "extra_source", "missing_revision", "nan_confidence", "infinite_confidence", "boolean_version", "lower_currency", "invalid_date", "fabricated_quote", "foreign_predecessor", "blank_source"])
def test_strict_boundary_rejects_malformed_output(variant):
    value = deepcopy(candidate())
    c = value['candidates'][0]
    evidence = [{"evidence_id": "e1", "text": "Refund INR 4999"}]
    if variant == "extra_candidate": c['unexpected'] = True
    if variant == "extra_terms": c['terms']['unexpected'] = True
    if variant == "missing_nullable": del c['terms']['due_at']
    if variant == "extra_source": c['sources'][0]['unexpected'] = True
    if variant == "missing_revision": del c['revision']['supersedes_id']
    if variant == "nan_confidence": c['confidence'] = float('nan')
    if variant == "infinite_confidence": c['confidence'] = float('inf')
    if variant == "boolean_version": value['schema_version'] = True
    if variant == "lower_currency": c['terms']['currency'] = 'inr'
    if variant == "invalid_date": c['terms']['due_at'] = '2026-02-30T00:00:00Z'
    if variant == "fabricated_quote": c['sources'][0]['quote'] = 'Not in evidence'
    if variant == "foreign_predecessor": c['revision'].update(relation='revision', supersedes_id='foreign')
    if variant == "blank_source": evidence[0]['text'] = ''
    with pytest.raises(AIInvalidOutputError):
        validate_ai_extraction_output(value, evidence, [])


def test_valid_boundary_preserves_null_and_source():
    value = candidate()
    validate_ai_extraction_output(value, [{"evidence_id": "e1", "text": "Refund INR 4999"}], [])
    assert value['candidates'][0]['terms']['due_at'] is None


def test_date_only_and_business_days_require_confirmation():
    for deadline in [DeadlineInfo(deadline_type='absolute_date', absolute_date='2026-11-20'), DeadlineInfo(deadline_type='duration', duration_value=3, duration_unit='business_days')]:
        warnings = []
        assert _confirmed_deadline(SimpleNamespace(deadline=deadline), '2026-11-14T10:00:00Z', warnings) is None
        assert warnings


def test_elapsed_deadline_requires_known_original_time():
    deadline = DeadlineInfo(deadline_type='duration', duration_value=48, duration_unit='hours')
    warnings = []
    assert _confirmed_deadline(SimpleNamespace(deadline=deadline), None, warnings) is None
    assert _confirmed_deadline(SimpleNamespace(deadline=deadline), '2026-11-14T10:00:00Z', []) == '2026-11-16T10:00:00Z'


def test_timezone_aware_absolute_deadline_normalizes_to_utc():
    deadline = DeadlineInfo(deadline_type='absolute_date', absolute_date='2026-11-20T23:59:00+05:30')
    assert _confirmed_deadline(SimpleNamespace(deadline=deadline), None, []) == '2026-11-20T18:29:00Z'
