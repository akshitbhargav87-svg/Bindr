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
├── document_processor.py           # DocumentProcessor (PyMuPDF for PDFs, Pillow for images)
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
│   └── test_document_processing.py # Milestone 2 document & evidence tests (9 tests)
├── requirements-ai.txt             # Proposed dependencies for backend owner
├── DEPENDENCIES.md                 # Dependencies & configuration guide
├── .env.example                    # Environment template
└── README.md                       # This documentation
```

---

## 2. Evidence-to-Promise Pipeline (Milestone 2)

### 2.1 Usage Example

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

### 2.2 Supported Document Formats
- **PDF Documents (`.pdf`)**: Extracted page-by-page using PyMuPDF (`fitz`), preserving page numbers (`Page 1`, `Page 2`, etc.).
- **Screenshot Images (`.png`, `.jpg`, `.jpeg`)**: Validated with Pillow (`PIL`), processed in-memory without persistent disk leaks.
- **Unsupported formats**: Clear typed exception `UnsupportedFileTypeError`.
- **Empty or corrupt files**: Handled gracefully via `UnreadableDocumentError` or returned as safe degraded result requiring user confirmation.

---

## 3. Evidence Traceability (`EvidenceMetadata`)

Every extracted commitment carries evidence traceability:

| Field | Type | Description |
| :--- | :--- | :--- |
| `evidence_id` | `Optional[str]` | Unique identifier for the source evidence. |
| `filename` | `Optional[str]` | Original filename of the document or screenshot. |
| `file_type` | `Optional[str]` | Detected file format (`pdf`, `png`, `jpg`, `jpeg`). |
| `total_pages` | `Optional[int]` | Total page count in document. |
| `page_numbers` | `List[int]` | Page numbers where text was extracted. |
| `extraction_warnings` | `List[str]` | Any warnings encountered (e.g. scanned image PDF). |

---

## 4. Running Tests

Tests run independently without requiring FastAPI or database connections:

```bash
# Run all 21 automated tests:
python -m unittest discover -s backend/app/ai/tests -v
```
