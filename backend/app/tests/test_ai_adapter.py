import pytest
from backend.app.core.config import settings
from backend.app.services.ai_adapter import (
    AIModuleAdapter,
    AIValidationError,
    AITimeoutError,
    AIServiceUnavailableError,
    AIInvalidOutputError,
)
from backend.app.ai.providers.base import (
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseParsingError,
)
from backend.app.ai.providers.meta import MetaProvider


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


def test_ai_adapter_missing_meta_key_raises_ai_unavailable_no_silent_mock():
    """Production Meta mode MUST NOT silently switch to mock when API key is missing."""
    adapter = AIModuleAdapter()
    adapter._engine = None

    settings.AI_PROVIDER = "meta"
    settings.MODEL_API_KEY = None

    with pytest.raises(AIServiceUnavailableError) as exc_info:
        adapter.extract_commitments(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[{"evidence_id": "e1", "text": "Refund promised of INR 1000."}]
        )
    assert exc_info.value.code == "AI_UNAVAILABLE"
    assert "MODEL_API_KEY" in str(exc_info.value) or "Meta API key" in str(exc_info.value)


def test_ai_adapter_explicit_mock_provider():
    """Mock mode explicitly selected executes offline extraction."""
    adapter = AIModuleAdapter()
    adapter._engine = None

    settings.AI_PROVIDER = "mock"
    settings.MODEL_API_KEY = None

    result = adapter.extract_commitments(
        case_id="11111111-1111-4111-8111-111111111111",
        evidence=[{"evidence_id": "e1", "text": "We will refund INR 500 within 7 days."}]
    )

    assert result["schema_version"] == 1
    assert "candidates" in result
    assert len(result["candidates"]) > 0
    candidate = result["candidates"][0]
    assert candidate["terms"]["kind"] in ["refund", "replacement", "service", "other"]
    assert len(candidate["sources"]) > 0


def test_ai_adapter_provider_selection_meta():
    """Verify Meta provider initialization reads settings correctly."""
    adapter = AIModuleAdapter()
    adapter._engine = None

    settings.AI_PROVIDER = "meta"
    settings.MODEL_API_KEY = "test-secret-key"
    settings.META_MODEL = "muse-spark-1.3"
    settings.META_BASE_URL = "https://api.meta.ai/v1"

    engine = adapter._get_engine()
    assert isinstance(engine.provider, MetaProvider)
    assert engine.provider.api_key == "test-secret-key"
    assert engine.provider.model_name == "muse-spark-1.3"
    assert engine.provider.base_url == "https://api.meta.ai/v1"


def test_ai_adapter_meta_connection_error_mapping():
    adapter = AIModuleAdapter()

    class ConnectionErrorEngine:
        def extract(self, text):
            raise AIConnectionError("Failed to establish connection to Meta Model API.")

    adapter._engine = ConnectionErrorEngine()

    with pytest.raises(AIServiceUnavailableError) as exc_info:
        adapter.extract_commitments(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[{"evidence_id": "e1", "text": "Valid text"}]
        )
    assert exc_info.value.code == "AI_UNAVAILABLE"


def test_ai_adapter_meta_rate_limit_error_mapping():
    adapter = AIModuleAdapter()

    class RateLimitEngine:
        def extract(self, text):
            raise AIRateLimitError("Meta API rate limit exceeded.")

    adapter._engine = RateLimitEngine()

    with pytest.raises(AIServiceUnavailableError) as exc_info:
        adapter.extract_commitments(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[{"evidence_id": "e1", "text": "Valid text"}]
        )
    assert exc_info.value.code == "AI_UNAVAILABLE"


def test_ai_adapter_meta_parsing_error_mapping():
    adapter = AIModuleAdapter()

    class ParsingErrorEngine:
        def extract(self, text):
            raise AIResponseParsingError("Model output violated JSON schema.")

    adapter._engine = ParsingErrorEngine()

    with pytest.raises(AIInvalidOutputError) as exc_info:
        adapter.extract_commitments(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[{"evidence_id": "e1", "text": "Valid text"}]
        )
    assert exc_info.value.code == "AI_INVALID_OUTPUT"


def test_ai_adapter_verbatim_quote_validation():
    adapter = AIModuleAdapter()

    class BadQuoteEngine:
        def extract(self, text):
            class BadResult:
                commitment_category = type("Cat", (), {"value": "refund"})
                commitment_description = "Fabricated refund"
                supporting_quotation = "This quote never appeared in the evidence text"
                missing_or_ambiguous_fields = []
                amount = None
                currency = None
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

    with pytest.raises(AITimeoutError) as exc_info:
        adapter.extract_commitments(
            case_id="11111111-1111-4111-8111-111111111111",
            evidence=[{"evidence_id": "e1", "text": "Some text"}]
        )
    assert exc_info.value.code == "AI_TIMEOUT"
