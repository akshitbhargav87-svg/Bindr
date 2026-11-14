import pytest
from backend.app.services.ai_adapter import (
    AIModuleAdapter,
    AIValidationError,
    AITimeoutError,
    AIServiceUnavailableError,
    AIInvalidOutputError
)


def test_ai_adapter_input_validation():
    adapter = AIModuleAdapter()

    # Empty evidence list
    with pytest.raises(AIValidationError) as exc:
        adapter.prepare_extraction_input(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[],
            existing_commitments=[]
        )
    assert "at least one evidence item" in str(exc.value)

    # Exceeding 10 items
    excess_evidence = [{"evidence_id": f"e{i}", "text": "Refund promised"} for i in range(11)]
    with pytest.raises(AIValidationError) as exc:
        adapter.prepare_extraction_input(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=excess_evidence,
            existing_commitments=[]
        )
    assert "at most 10" in str(exc.value)

    # Exceeding 50,000 character limit
    long_text = "A" * 50001
    with pytest.raises(AIValidationError) as exc:
        adapter.prepare_extraction_input(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[{"evidence_id": "e1", "text": long_text}],
            existing_commitments=[]
        )
    assert "50,000 characters" in str(exc.value)


def test_ai_adapter_mock_fallback_contract_compliance():
    adapter = AIModuleAdapter()
    evidence_text = "We will refund INR 4999.00 for order DEMO-42 by 18 November 2026."
    evidence = [{"evidence_id": "22222222-2222-4222-8222-222222222222", "text": evidence_text}]

    output = adapter._mock_extraction_contract_response({
        "schema_version": 1,
        "case_id": "11111111-1111-4111-8111-111111111111",
        "evidence": evidence,
        "existing_commitments": []
    })

    assert output["schema_version"] == 1
    assert "candidates" in output
    assert len(output["candidates"]) == 1
    candidate = output["candidates"][0]

    # Check AI_CONTRACT shape
    assert candidate["candidate_id"] == "c1"
    assert "terms" in candidate
    assert candidate["terms"]["kind"] == "refund"
    assert "sources" in candidate
    source = candidate["sources"][0]
    assert source["evidence_id"] == "22222222-2222-4222-8222-222222222222"
    # Quote must be a verbatim substring of original evidence text
    assert source["quote"] in evidence_text
    assert "revision" in candidate
    assert candidate["revision"]["relation"] == "new"


def test_ai_adapter_verbatim_quote_validation():
    adapter = AIModuleAdapter()
    # Simulated engine generating non-verbatim quote
    class BadQuoteEngine:
        def extract(self, text):
            class BadResult:
                commitment_category = type("Cat", (), {"value": "refund"})
                commitment_description = "Fabricated refund"
                source_quote = "This quote never appeared in the evidence text"
                missing_or_ambiguous_fields = []
            return BadResult()

    adapter._engine = BadQuoteEngine()

    with pytest.raises(AIInvalidOutputError) as exc:
        adapter.extract_commitments(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[{"evidence_id": "e1", "text": "Original true text"}]
        )
    assert "not an exact verbatim substring" in str(exc.value)


def test_ai_adapter_timeout_mapping():
    adapter = AIModuleAdapter()
    class TimeoutEngine:
        def extract(self, text):
            raise TimeoutError("Model provider request timed out after 45s")

    adapter._engine = TimeoutEngine()

    with pytest.raises(AITimeoutError):
        adapter.extract_commitments(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[{"evidence_id": "e1", "text": "Some text"}]
        )
