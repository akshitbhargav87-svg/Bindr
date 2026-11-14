# Promise Keeper - AI Extraction Engine (Milestone 1)

This module implements **Milestone 1: Promise Extraction Engine** for Promise Keeper.

It converts raw text extracted from company communications (emails, chat screenshots, letters, PDFs) into structured, validated commitment data.

---

## 1. AI Contract Specification (Temporary Contract)

Until `docs/AI_CONTRACT.md` is finalized across teams, this contract defines the interface between `backend/app/ai/` and the backend business logic/routers.

### 1.1 Input Specification

```python
from backend.app.ai import extract_commitment, SourceMetadata

metadata = SourceMetadata(
    sender="Acme Corp",                   # Optional[str]: Company/agent name or email
    recipient="Customer",                 # Optional[str]: Customer name or email
    communication_date="2026-11-14",      # Optional[str]: Date of message (ISO or text)
    channel="email",                      # Optional[str]: 'email', 'chat_screenshot', 'pdf', 'sms'
    subject="Your return request",        # Optional[str]: Subject line
    extra={}                              # Dict[str, Any]: Client-specific metadata
)

result = extract_commitment(
    text="A refund of $120.50 will be credited to your account within 5-7 business days.",
    metadata=metadata,
    fallback_on_error=True                # Safe degraded result instead of unhandled crash
)
```

### 1.2 Output Specification (`CommitmentExtractionResult`)

The extraction engine returns a validated Pydantic model:

| Field | Type | Description |
| :--- | :--- | :--- |
| `company_name` | `Optional[str]` | Company making or declining the commitment (`null` if unknown). |
| `commitment_category` | `CommitmentCategory` | Enum: `refund`, `replacement`, `repair`, `cancellation`, `service_credit`, `delivery`, `callback`, `status_update`, `other`, `no_commitment`. |
| `commitment_description` | `str` | Concise factual summary of what was promised. |
| `amount` | `Optional[float]` | Numeric monetary amount (`null` if not applicable). |
| `currency` | `Optional[str]` | Currency code or symbol (`null` if not applicable). |
| `communication_date` | `Optional[str]` | Date of communication (`null` if unknown). |
| `deadline` | `DeadlineInfo` | Structured duration or absolute date (see below). |
| `commitment_type` | `CommitmentType` | Enum: `explicit` (firm promise), `inferred` (implied/conditional/vague), `none` (no promise). |
| `is_vague_estimate` | `bool` | `true` if language is non-binding (e.g., "usually takes a few days"). |
| `supporting_quotation` | `Optional[str]` | Exact verbatim quotation copied from the input text. |
| `missing_or_ambiguous_fields` | `List[str]` | List of ambiguous or missing fields (e.g., `["amount", "deadline"]`). |
| `user_confirmation_required` | `bool` | `true` if human-in-the-loop review is recommended (vague estimate, inferred commitment, missing fields, or quote mismatch). |
| `raw_source_text` | `Optional[str]` | Raw input text analyzed (retained for verification and backend audit logging). |

### 1.3 Deadline Specification (`DeadlineInfo`)

> **IMPORTANT ARCHITECTURAL RULE:**  
> The LLM **does NOT** compute business-day or holiday deadlines. The LLM extracts raw duration numbers and units. The backend owns holiday calendars and business-day calculation.

```python
class DeadlineInfo(BaseModel):
    deadline_type: DeadlineType  # 'duration', 'absolute_date', or 'none'
    duration_value: Optional[float]  # e.g., 5.0
    duration_value_max: Optional[float]  # e.g., 7.0 (when a range like "5-7 days" is promised)
    duration_unit: Optional[str]  # 'business_days', 'calendar_days', 'hours', 'weeks', 'months'
    absolute_date: Optional[str]  # e.g., "Monday" or "2026-11-20" if explicitly specified
    raw_deadline_text: Optional[str]  # verbatim snippet: "within 5-7 business days"
```

---

## 2. Core Design Principles & Guarantees

1. **Return `null` for unknown information**: Empty or missing attributes are `None`, never placeholder strings like `"N/A"` or `"unknown"`.
2. **Distinguish promises from vague estimates**: Vague estimates (`"usually takes 3 days"`) are flagged as `is_vague_estimate=True`, `commitment_type=INFERRED`, and automatically enforce `user_confirmation_required=True`.
3. **Preserve exact source quotations**: The supporting quotation is verified against the input text. If not verbatim, it is flagged as ambiguous and requires user confirmation.
4. **No fabricated confidence scores**: Numerical confidence scores (e.g. `0.95`) are intentionally omitted. Qualitative certainty is captured through `commitment_type`, `missing_or_ambiguous_fields`, and `user_confirmation_required`.
5. **Configurable AI Provider Interface**: Supports `GeminiProvider` (production) and `MockAIProvider` (tests/offline), dynamically selectable via environment variable or dependency injection.
6. **Graceful error boundaries**: Handles malformed model outputs and unavailable credentials safely without crashing backend processes.

---

## 3. Directory Layout

```text
backend/app/ai/
├── __init__.py               # Public API exports
├── engine.py                 # PromiseExtractionEngine & extract_commitment function
├── schemas.py                # Pydantic data models & contract validators
├── prompts.py                # System instructions & user extraction templates
├── providers/
│   ├── __init__.py           # Provider exports
│   ├── base.py               # AIProvider ABC & custom exceptions
│   ├── gemini.py             # GeminiProvider implementation (REST / API)
│   ├── mock.py               # MockAIProvider for deterministic testing
│   └── factory.py            # get_ai_provider resolution factory
├── tests/
│   ├── __init__.py
│   └── test_extraction.py    # 10 comprehensive unit & synthetic test cases
├── requirements-ai.txt       # Proposed dependencies for backend owner
├── DEPENDENCIES.md           # Documentation for backend owner
└── README.md                 # This contract and integration guide
```

---

## 4. Running the Tests

Tests run independently of the frontend and external services:

```bash
# Using Python's built-in unittest:
python -m unittest backend.app.ai.tests.test_extraction -v

# Or using pytest (if installed):
pytest backend/app/ai/tests/ -v
```
