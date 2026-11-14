# Promise Keeper (Bindr) — AI Backend (Milestones 1 & 2)

This module implements:
- **Milestone 1**: Promise Extraction Engine using Meta Model API (`muse-spark-1.3`).
- **Milestone 2**: Document and Image Processing & Evidence-to-Promise Pipeline.

---

## 1. Architecture Overview

```text
backend/app/ai/
├── __init__.py                     # Package public exports
├── engine.py                       # PromiseExtractionEngine & extract_commitment_from_evidence
├── schemas.py                      # Pydantic schemas (CommitmentExtractionResult, EvidenceMetadata)
├── prompts.py                      # Extraction system prompts & templates
├── document_processor.py           # DocumentProcessor (PyMuPDF for PDFs, RapidOCR for images, plain text)
├── env.py                          # Lightweight .env loader
├── providers/
│   ├── __init__.py
│   ├── base.py                     # AIProvider interface & typed exceptions
│   ├── meta.py                     # Meta Model API provider (muse-spark-1.3)
│   ├── mock.py                     # Deterministic mock provider
│   └── factory.py                  # Dynamic provider factory
├── tests/
│   ├── __init__.py
│   ├── test_extraction.py          # Milestone 1 extraction tests (12 tests)
│   └── test_document_processing.py # Milestone 2 document & evidence tests (14 tests)
├── requirements-ai.txt             # Proposed dependencies for backend owner
├── DEPENDENCIES.md                 # Dependencies & configuration guide
├── .env.example                    # Environment template
└── README.md                       # This documentation
```

---

## 2. Environment Variables

| Variable | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `MODEL_API_KEY` | Yes (meta mode) | — | Meta Model API Bearer token |
| `AI_PROVIDER` | No | auto-detected | `"meta"` or `"mock"` |
| `META_BASE_URL` | No | `https://api.meta.ai/v1` | Meta API base URL override |
| `META_MODEL` | No | `muse-spark-1.3` | Model identifier |
| `META_TIMEOUT` | No | `30` | Request timeout in seconds |

> **Strict-meta guarantee:** When `AI_PROVIDER="meta"` is set, the factory **always** returns `MetaProvider`.
> It will never silently fall back to `MockAIProvider`. If `MODEL_API_KEY` is absent,
> `AIAuthenticationError` is raised at the first API call — not at startup.

---

## 3. Integration Guide for Backend (Lokesh)

### 3.1 Minimal Callable Example

```python
# In your FastAPI route or service layer:
from backend.app.ai import extract_commitment_from_evidence, SourceMetadata

async def process_evidence_upload(
    file_bytes: bytes,
    original_filename: str,
    evidence_id: str,
    sender_name: str | None = None,
):
    """
    Call this after saving the file to your database/storage.
    The AI module does NOT persist anything — pass bytes, receive structured result.
    """
    result = extract_commitment_from_evidence(
        file_source=file_bytes,          # bytes from FastAPI UploadFile.read()
        filename=original_filename,      # e.g. "refund_chat.png" / "ticket.pdf" / "email.txt"
        evidence_id=evidence_id,         # your DB record ID, e.g. "ev_8f3a1c"
        metadata=SourceMetadata(
            sender=sender_name,          # e.g. "Flipkart Support"
        ),
        fallback_on_error=True,          # returns safe degraded result instead of raising on AI errors
    )

    # result is a fully validated CommitmentExtractionResult (Pydantic model)
    return result.model_dump()
```

### 3.2 Key Response Fields

```python
result.commitment_category       # CommitmentCategory enum: REFUND, DELIVERY, etc.
result.commitment_type           # CommitmentType enum: EXPLICIT / INFERRED / NONE
result.amount                    # float | None — extracted monetary amount
result.currency                  # str | None — "INR", "USD", etc.
result.deadline                  # DeadlineInfo | None — {duration_value, duration_unit, deadline_date}
result.supporting_quotation      # str | None — verbatim quote from source text
result.company_name              # str | None
result.user_confirmation_required  # bool — True means human review needed
result.evidence_metadata         # EvidenceMetadata — traceability back to source file
result.evidence_metadata.evidence_id  # your passed evidence_id echoed back
result.evidence_metadata.page_numbers # [1, 2, ...] pages where text was found
```

### 3.3 Supported File Types

| Extension | Handler |
| :--- | :--- |
| `.pdf` | PyMuPDF — text layer extracted page-by-page |
| `.png` / `.jpg` / `.jpeg` | Pillow + RapidOCR (onnxruntime) |
| `.txt` | UTF-8 / latin-1 decode |

### 3.4 Error Handling

```python
from backend.app.ai.document_processor import UnsupportedFileTypeError, UnreadableDocumentError
from backend.app.ai.providers.base import AIAuthenticationError, AIConnectionError, AIRateLimitError

try:
    result = extract_commitment_from_evidence(file_source=data, filename=fname, evidence_id=eid)
except UnsupportedFileTypeError as e:
    # Return HTTP 422 — file format not supported
    raise HTTPException(status_code=422, detail=str(e))
except UnreadableDocumentError as e:
    # Return HTTP 400 — corrupt or empty file
    raise HTTPException(status_code=400, detail=str(e))
except AIAuthenticationError:
    # MODEL_API_KEY is missing or invalid
    raise HTTPException(status_code=503, detail="AI service not configured.")
except AIConnectionError:
    # Network timeout or Meta API unreachable
    raise HTTPException(status_code=503, detail="AI service temporarily unavailable.")
```

---

## 4. Evidence-to-Promise Pipeline (Milestone 2)

### 4.1 Usage Example

```python
from backend.app.ai import extract_commitment_from_evidence, SourceMetadata

# 1. Processing from file path
result = extract_commitment_from_evidence(
    file_source="path/to/customer_email.pdf",
    evidence_id="ev_12345",
    metadata=SourceMetadata(sender="Acme Corp")
)

# 2. Processing from raw in-memory bytes (e.g. from FastAPI file upload)
result = extract_commitment_from_evidence(
    file_source=uploaded_file_bytes,
    filename="refund_receipt.png",
    evidence_id="ev_67890"
)

# Access extracted promise and evidence traceability
print(result.company_name)            # "Acme Corp"
print(result.amount)                  # 120.50
print(result.currency)                # "USD"
print(result.supporting_quotation)    # "We will refund $120.50..."
print(result.evidence_metadata)       # EvidenceMetadata(evidence_id='ev_12345', filename='customer_email.pdf', ...)
```

### 4.2 Supported Document Formats
- **PDF Documents (`.pdf`)**: Extracted page-by-page using PyMuPDF (`fitz`), preserving page numbers (`Page 1`, `Page 2`, etc.).
- **Screenshot Images (`.png`, `.jpg`, `.jpeg`)**: Validated with Pillow (`PIL`), OCR via RapidOCR + onnxruntime.
- **Plain Text (`.txt`)**: UTF-8 / latin-1 decoding, treated as a single-page document.
- **Unsupported formats**: Clear typed exception `UnsupportedFileTypeError`.
- **Empty or corrupt files**: Handled gracefully via `UnreadableDocumentError` or returned as safe degraded result requiring user confirmation.

---

## 5. Evidence Traceability (`EvidenceMetadata`)

Every extracted commitment carries evidence traceability:

| Field | Type | Description |
| :--- | :--- | :--- |
| `evidence_id` | `Optional[str]` | Unique identifier for the source evidence. |
| `filename` | `Optional[str]` | Original filename of the document or screenshot. |
| `file_type` | `Optional[str]` | Detected file format (`pdf`, `png`, `jpg`, `jpeg`, `txt`). |
| `total_pages` | `Optional[int]` | Total page count in document. |
| `page_numbers` | `List[int]` | Page numbers where text was extracted. |
| `extraction_warnings` | `List[str]` | Any warnings encountered (e.g. scanned image PDF). |

---

## 6. Running Tests

Tests run independently without requiring FastAPI or database connections:

```bash
# Run all automated tests:
cd /path/to/Bindr
python -m unittest discover -s backend/app/ai/tests -v
```
