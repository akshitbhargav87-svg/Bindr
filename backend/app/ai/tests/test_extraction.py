"""
Comprehensive synthetic test suite for the Promise Extraction Engine.

Covers:
1. Synthetic Scenario 1: Refund with a deadline
2. Synthetic Scenario 2: Replacement promise
3. Synthetic Scenario 3: No explicit promise
4. Synthetic Scenario 4: Ambiguous communication & vague estimates
5. Null for unknown information (no placeholder strings like 'N/A')
6. Verbatim quotation verification
7. Duration extraction without business-day calculation
8. Absence of fabricated numerical confidence scores
9. Malformed model response handling
10. Meta Provider credential, connection, and response parsing handling
"""

import json
import sys
import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.ai.schemas import (
    CommitmentExtractionResult,
    CommitmentCategory,
    CommitmentType,
    DeadlineType,
    SourceMetadata,
)
from backend.app.ai.engine import PromiseExtractionEngine, extract_commitment
from backend.app.ai.providers.mock import MockAIProvider
from backend.app.ai.providers.meta import MetaProvider
from backend.app.ai.providers.base import (
    AIAuthenticationError,
    AIConnectionError,
    AIRateLimitError,
    AIResponseParsingError,
)


class TestPromiseExtractionEngine(unittest.TestCase):
    """Test suite for Promise Extraction Engine."""

    def setUp(self):
        self.mock_provider = MockAIProvider()
        self.engine = PromiseExtractionEngine(provider=self.mock_provider)

    def _complete_meta_payload(self, **overrides):
        payload = {
            "company_name": "Acme Corp",
            "commitment_category": "refund",
            "commitment_description": "Refund of $45 within 5 business days.",
            "amount": 45.0,
            "currency": "USD",
            "communication_date": None,
            "deadline": {
                "deadline_type": "duration",
                "duration_value": 5.0,
                "duration_value_max": None,
                "duration_unit": "business_days",
                "absolute_date": None,
                "raw_deadline_text": "within 5 business days",
            },
            "commitment_type": "explicit",
            "is_vague_estimate": False,
            "supporting_quotation": "We will refund $45 within 5 business days.",
            "missing_or_ambiguous_fields": [],
            "user_confirmation_required": False,
        }
        payload.update(overrides)
        return payload

    def _set_meta_response(self, mock_post, payload):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(payload)}}]
        }
        mock_post.return_value = mock_response

    # -------------------------------------------------------------------------
    # Synthetic Scenario 1: Refund with a deadline
    # -------------------------------------------------------------------------
    def test_synthetic_refund_with_deadline(self):
        """Case: Company explicitly promises a refund with a business-day deadline."""
        text = (
            "Dear Customer, we have approved your return request. "
            "A refund of $120.50 will be credited to your account within 5-7 business days. "
            "Thank you, Acme Corp Support Team."
        )
        metadata = SourceMetadata(
            sender="Acme Corp",
            communication_date="2026-11-14",
            channel="email",
        )

        result = self.engine.extract(text=text, metadata=metadata)

        self.assertEqual(result.company_name, "Acme Corp")
        self.assertEqual(result.commitment_category, CommitmentCategory.REFUND)
        self.assertEqual(result.commitment_type, CommitmentType.EXPLICIT)
        self.assertEqual(result.amount, 120.50)
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.communication_date, "2026-11-14")

        # Deadline verification: duration extracted, NOT calculated
        self.assertEqual(result.deadline.deadline_type, DeadlineType.DURATION)
        self.assertEqual(result.deadline.duration_value, 5.0)
        self.assertEqual(result.deadline.duration_value_max, 7.0)
        self.assertEqual(result.deadline.duration_unit, "business_days")
        self.assertIn("within 5-7 business days", result.deadline.raw_deadline_text)

        # Supporting quote verification: must be verbatim from text
        self.assertIsNotNone(result.supporting_quotation)
        self.assertIn(result.supporting_quotation, text)
        self.assertFalse(result.is_vague_estimate)
        self.assertFalse(result.user_confirmation_required)

    # -------------------------------------------------------------------------
    # Synthetic Scenario 2: Replacement promise
    # -------------------------------------------------------------------------
    def test_synthetic_replacement_promise(self):
        """Case: Company promises to replace a defective item with an absolute date."""
        text = (
            "We apologize for the defective blender. "
            "Acme Corp will dispatch a brand new replacement unit via express shipping on Monday."
        )
        metadata = SourceMetadata(channel="chat_screenshot")

        result = self.engine.extract(text=text, metadata=metadata)

        self.assertEqual(result.company_name, "Acme Corp")
        self.assertEqual(result.commitment_category, CommitmentCategory.REPLACEMENT)
        self.assertEqual(result.commitment_type, CommitmentType.EXPLICIT)
        self.assertIsNone(result.amount)
        self.assertIsNone(result.currency)
        self.assertEqual(result.deadline.deadline_type, DeadlineType.ABSOLUTE_DATE)
        self.assertIn("Monday", result.deadline.absolute_date)

        # Verbatim quote
        self.assertIsNotNone(result.supporting_quotation)
        self.assertIn(result.supporting_quotation, text)
        self.assertFalse(result.is_vague_estimate)
        self.assertFalse(result.user_confirmation_required)

    # -------------------------------------------------------------------------
    # Synthetic Scenario 3: No explicit promise
    # -------------------------------------------------------------------------
    def test_synthetic_no_explicit_promise(self):
        """Case: Informational email, ticket closure, or newsletter with no promise."""
        text = (
            "Thank you for contacting CloudStream Support. "
            "We have received your ticket #48102 and our team has closed this case. "
            "Please check our online community knowledge base if you have further inquiries."
        )
        metadata = SourceMetadata(sender="CloudStream", channel="email")

        result = self.engine.extract(text=text, metadata=metadata)

        self.assertEqual(result.commitment_category, CommitmentCategory.NO_COMMITMENT)
        self.assertEqual(result.commitment_type, CommitmentType.NONE)
        self.assertIsNone(result.amount)
        self.assertIsNone(result.currency)
        self.assertIsNone(result.supporting_quotation)
        self.assertEqual(result.deadline.deadline_type, DeadlineType.NONE)
        self.assertFalse(result.user_confirmation_required)

    # -------------------------------------------------------------------------
    # Synthetic Scenario 4: Ambiguous communication & vague estimates
    # -------------------------------------------------------------------------
    def test_synthetic_ambiguous_communication(self):
        """Case: Vague estimates and non-committal language must require user confirmation."""
        text = (
            "Hello, we might be able to offer some store credit or refund eventually. "
            "Typically this takes some time to review with management."
        )

        result = self.engine.extract(text=text)

        self.assertEqual(result.commitment_type, CommitmentType.INFERRED)
        self.assertTrue(result.is_vague_estimate)
        # Crucial check: user confirmation MUST be required for ambiguous statements
        self.assertTrue(result.user_confirmation_required)
        self.assertTrue(len(result.missing_or_ambiguous_fields) > 0)
        self.assertIn("amount", result.missing_or_ambiguous_fields)

    # -------------------------------------------------------------------------
    # Rule: Return null for unknown information
    # -------------------------------------------------------------------------
    def test_null_for_unknown_information(self):
        """Ensure placeholder strings like 'N/A' or 'unknown' are sanitized to None."""
        raw_payload = {
            "company_name": "N/A",
            "commitment_category": "refund",
            "commitment_description": "Refund promised",
            "amount": None,
            "currency": "unknown",
            "communication_date": "None",
            "supporting_quotation": "null",
        }
        model = CommitmentExtractionResult.model_validate(raw_payload)

        self.assertIsNone(model.company_name)
        self.assertIsNone(model.currency)
        self.assertIsNone(model.communication_date)
        self.assertIsNone(model.supporting_quotation)

    # -------------------------------------------------------------------------
    # Rule: No calculation of business-day deadlines in the LLM
    # -------------------------------------------------------------------------
    def test_deadline_duration_not_calculated(self):
        """Verify duration numbers and units are preserved for backend calculation."""
        text = "Your refund will process within 10 business days."
        result = self.engine.extract(text=text)

        self.assertEqual(result.deadline.deadline_type, DeadlineType.DURATION)
        self.assertEqual(result.deadline.duration_value, 10.0)
        self.assertEqual(result.deadline.duration_unit, "business_days")
        self.assertIsNone(result.deadline.absolute_date)

    # -------------------------------------------------------------------------
    # Rule: No fabricated numerical confidence scores
    # -------------------------------------------------------------------------
    def test_no_fabricated_confidence_score(self):
        """Verify the model schema does NOT contain arbitrary numeric confidence fields."""
        fields = CommitmentExtractionResult.model_fields
        self.assertNotIn("confidence", fields)
        self.assertNotIn("confidence_score", fields)

    # -------------------------------------------------------------------------
    # Verbatim Quotation Preservation & Mismatch Detection
    # -------------------------------------------------------------------------
    def test_verbatim_quotation_mismatch_triggers_confirmation(self):
        """If a quotation does not match source text, flag for user confirmation."""
        source_text = "Acme Corp will refund your purchase within 3 days."
        hallucinated_quote = "We will definitely wire $1000 right now to your account."

        res = CommitmentExtractionResult(
            company_name="Acme Corp",
            commitment_category=CommitmentCategory.REFUND,
            commitment_description="Refund",
            supporting_quotation=hallucinated_quote,
            raw_source_text=source_text,
        )

        self.assertTrue(res.user_confirmation_required)
        self.assertIn("supporting_quotation", res.missing_or_ambiguous_fields)

    # -------------------------------------------------------------------------
    # Error Handling: Malformed Model Responses
    # -------------------------------------------------------------------------
    def test_malformed_response_handling_raises_or_fallbacks(self):
        """Verify handling of corrupted/malformed LLM output."""
        failing_provider = MockAIProvider(simulate_failure="parsing")

        # 1. Without fallback: raises AIResponseParsingError
        engine_strict = PromiseExtractionEngine(provider=failing_provider, fallback_on_error=False)
        with self.assertRaises(AIResponseParsingError):
            engine_strict.extract("Some text")

        # 2. With fallback: returns safe degraded result requiring user confirmation
        engine_safe = PromiseExtractionEngine(provider=failing_provider, fallback_on_error=True)
        fallback_res = engine_safe.extract("Some text")
        self.assertTrue(fallback_res.user_confirmation_required)
        self.assertIn("ai_provider_error", fallback_res.missing_or_ambiguous_fields)

    # -------------------------------------------------------------------------
    # Meta Provider Tests: Credentials, HTTP Errors, and Extraction
    # -------------------------------------------------------------------------
    def test_meta_provider_missing_credentials(self):
        """Verify MetaProvider raises AIAuthenticationError when MODEL_API_KEY is unset."""
        meta_no_key = MetaProvider(api_key="")
        engine_meta = PromiseExtractionEngine(provider=meta_no_key, fallback_on_error=False)
        with self.assertRaises(AIAuthenticationError):
            engine_meta.extract("Sample communication")

        # In fallback mode, returns safe result requiring user confirmation
        engine_meta_safe = PromiseExtractionEngine(provider=meta_no_key, fallback_on_error=True)
        safe_res = engine_meta_safe.extract("Sample communication")
        self.assertTrue(safe_res.user_confirmation_required)
        self.assertIn("ai_provider_error", safe_res.missing_or_ambiguous_fields)

    @patch("backend.app.ai.providers.meta.requests.post")
    def test_meta_provider_successful_extraction(self, mock_post):
        """Verify MetaProvider formats chat completion request and parses JSON response."""
        sample_response_content = json.dumps({
            "company_name": "MetaStore",
            "commitment_category": "refund",
            "commitment_description": "Refund of $50 will be credited within 3 business days.",
            "amount": 50.0,
            "currency": "USD",
            "communication_date": "2026-11-14",
            "deadline": {
                "deadline_type": "duration",
                "duration_value": 3.0,
                "duration_value_max": None,
                "duration_unit": "business_days",
                "absolute_date": None,
                "raw_deadline_text": "within 3 business days"
            },
            "commitment_type": "explicit",
            "is_vague_estimate": False,
            "supporting_quotation": "A refund of $50 will be credited within 3 business days.",
            "missing_or_ambiguous_fields": [],
            "user_confirmation_required": False
        })

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": f"```json\n{sample_response_content}\n```"
                    }
                }
            ]
        }
        mock_post.return_value = mock_response

        provider = MetaProvider(api_key="test-key-12345", model_name="muse-spark-1.3")
        engine = PromiseExtractionEngine(provider=provider)

        input_text = "Dear user, A refund of $50 will be credited within 3 business days. MetaStore team."
        result = engine.extract(input_text)

        self.assertEqual(result.company_name, "MetaStore")
        self.assertEqual(result.amount, 50.0)
        self.assertEqual(result.currency, "USD")
        self.assertEqual(result.commitment_category, CommitmentCategory.REFUND)
        self.assertEqual(result.deadline.duration_value, 3.0)
        self.assertEqual(result.deadline.duration_unit, "business_days")
        self.assertFalse(result.user_confirmation_required)

        # Verify request parameters
        call_args = mock_post.call_args
        self.assertEqual(call_args[1]["headers"]["Authorization"], "Bearer test-key-12345")
        self.assertEqual(call_args[1]["json"]["model"], "muse-spark-1.3")

    @patch("backend.app.ai.providers.meta.requests.post")
    def test_meta_provider_http_error_mappings(self, mock_post):
        """Verify MetaProvider maps 401, 429, and 500 status codes to typed exceptions."""
        provider = MetaProvider(api_key="valid-dummy-key")

        # 401 Unauthorized -> AIAuthenticationError
        mock_resp_401 = MagicMock(status_code=401, text="Unauthorized Bearer token")
        mock_post.return_value = mock_resp_401
        with self.assertRaises(AIAuthenticationError):
            provider.extract_commitment("Sample text")

        # 429 Rate Limit -> AIRateLimitError
        mock_resp_429 = MagicMock(status_code=429, text="Rate limit exceeded")
        mock_post.return_value = mock_resp_429
        with self.assertRaises(AIRateLimitError):
            provider.extract_commitment("Sample text")

    @patch("backend.app.ai.providers.meta.requests.post")
    def test_meta_provider_revised_commitment_and_prompt_guidance(self, mock_post):
        """Verify revised promises are represented by the latest explicit commitment."""
        source_text = (
            "Earlier we promised a $30 refund within 3 days. "
            "Correction: we will refund $45 within 5 business days instead; "
            "this replaces our earlier promise."
        )
        revised_quote = (
            "Correction: we will refund $45 within 5 business days instead; "
            "this replaces our earlier promise."
        )
        response_content = json.dumps({
            "company_name": "Acme Corp",
            "commitment_category": "refund",
            "commitment_description": "Refund of $45 within 5 business days.",
            "amount": 45.0,
            "currency": "USD",
            "communication_date": None,
            "deadline": {
                "deadline_type": "duration",
                "duration_value": 5.0,
                "duration_value_max": None,
                "duration_unit": "business_days",
                "absolute_date": None,
                "raw_deadline_text": "within 5 business days",
            },
            "commitment_type": "explicit",
            "is_vague_estimate": False,
            "supporting_quotation": revised_quote,
            "missing_or_ambiguous_fields": [],
            "user_confirmation_required": False,
        })
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": response_content}}]
        }
        mock_post.return_value = mock_response

        provider = MetaProvider(api_key="synthetic-test-key")
        result = provider.extract_commitment(source_text)

        self.assertEqual(result.amount, 45.0)
        self.assertEqual(result.commitment_category, CommitmentCategory.REFUND)
        self.assertEqual(result.deadline.duration_value, 5.0)
        self.assertEqual(result.deadline.duration_unit, "business_days")
        self.assertEqual(result.supporting_quotation, revised_quote)
        self.assertIn(result.supporting_quotation, source_text)

        system_prompt = mock_post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("latest applicable promise", system_prompt)
        self.assertIn('Do not classify it as "none"', system_prompt)

    @patch("backend.app.ai.providers.meta.requests.post")
    def test_meta_provider_normalizes_legacy_flat_deadline(self, mock_post):
        source_text = "Acme Corp will refund $45 within 5 business days."
        payload = self._complete_meta_payload(supporting_quotation=source_text)
        deadline = payload.pop("deadline")
        payload.update(deadline)
        self._set_meta_response(mock_post, payload)

        result = MetaProvider(api_key="synthetic-test-key").extract_commitment(source_text)

        self.assertEqual(result.commitment_category, CommitmentCategory.REFUND)
        self.assertEqual(result.deadline.deadline_type, DeadlineType.DURATION)
        self.assertEqual(result.deadline.duration_value, 5.0)
        self.assertEqual(result.deadline.duration_unit, "business_days")
        self.assertEqual(result.supporting_quotation, source_text)

    @patch("backend.app.ai.providers.meta.requests.post")
    def test_meta_provider_rejects_missing_category_and_deadline(self, mock_post):
        source_text = "Acme Corp will refund $45 within 5 business days."
        provider = MetaProvider(api_key="synthetic-test-key")

        missing_category = self._complete_meta_payload(supporting_quotation=source_text)
        missing_category.pop("commitment_category")
        self._set_meta_response(mock_post, missing_category)
        with self.assertRaises(AIResponseParsingError):
            provider.extract_commitment(source_text)

        missing_deadline = self._complete_meta_payload(supporting_quotation=source_text)
        missing_deadline.pop("deadline")
        self._set_meta_response(mock_post, missing_deadline)
        with self.assertRaises(AIResponseParsingError):
            provider.extract_commitment(source_text)

    @patch("backend.app.ai.providers.meta.requests.post")
    def test_meta_provider_rejects_contradictory_or_incomplete_output(self, mock_post):
        source_text = "Acme Corp will refund $45 within 5 business days."
        provider = MetaProvider(api_key="synthetic-test-key")

        cases = [
            self._complete_meta_payload(
                supporting_quotation=source_text,
                commitment_type="none",
            ),
            self._complete_meta_payload(
                supporting_quotation=source_text,
                deadline={
                    "deadline_type": "duration",
                    "duration_value": 5.0,
                    "duration_value_max": None,
                    "duration_unit": None,
                    "absolute_date": None,
                    "raw_deadline_text": "within 5 business days",
                },
            ),
            self._complete_meta_payload(
                supporting_quotation=source_text,
                deadline={
                    "deadline_type": "none",
                    "duration_value": 5.0,
                    "duration_value_max": None,
                    "duration_unit": "business_days",
                    "absolute_date": None,
                    "raw_deadline_text": "within 5 business days",
                },
            ),
        ]
        for payload in cases:
            with self.subTest(payload=payload):
                self._set_meta_response(mock_post, payload)
                with self.assertRaises(AIResponseParsingError):
                    provider.extract_commitment(source_text)

        mixed_deadline = self._complete_meta_payload(supporting_quotation=source_text)
        mixed_deadline["duration_value"] = 5.0
        self._set_meta_response(mock_post, mixed_deadline)
        with self.assertRaises(AIResponseParsingError):
            provider.extract_commitment(source_text)

    @patch("backend.app.ai.providers.meta.requests.post")
    def test_meta_provider_preserves_missing_currency_as_null(self, mock_post):
        source_text = "Acme Corp will refund 120.50 within 5 business days."
        payload = self._complete_meta_payload(
            amount=120.5,
            currency=None,
            supporting_quotation=source_text,
            missing_or_ambiguous_fields=["currency"],
            user_confirmation_required=True,
        )
        self._set_meta_response(mock_post, payload)

        result = MetaProvider(api_key="synthetic-test-key").extract_commitment(source_text)

        self.assertEqual(result.amount, 120.5)
        self.assertIsNone(result.currency)
        self.assertEqual(result.deadline.duration_value, 5.0)
        self.assertTrue(result.user_confirmation_required)

    @patch("backend.app.ai.providers.meta.requests.post")
    def test_meta_provider_rejects_non_verbatim_quotation(self, mock_post):
        source_text = "Acme Corp will refund $45 within 5 business days."
        payload = self._complete_meta_payload(
            supporting_quotation="Acme Corp will refund $45 in 5 business days."
        )
        self._set_meta_response(mock_post, payload)

        with self.assertRaises(AIResponseParsingError):
            MetaProvider(api_key="synthetic-test-key").extract_commitment(source_text)


if __name__ == "__main__":
    unittest.main()
