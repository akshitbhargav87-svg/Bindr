# AI Module Dependencies (Milestones 1 & 2 + OCR)

**Target Audience:** Backend Lead / Backend Developer  
**Location:** `backend/app/ai/`

---

## 1. Overview
In accordance with AI ownership rules, the shared root `requirements.txt` was not modified directly. The proposed dependencies below are required for the **Promise Extraction Engine, Evidence Processing Pipeline, and Screenshot OCR** using the **Meta Model API**.

---

## 2. Dependency List & Justification

| Package | Recommended Version | Purpose | Is Required? |
| :--- | :--- | :--- | :--- |
| **`pydantic`** | `>=2.7.0, <3.0.0` | High-performance schema validation, serialization, and contract enforcement for `CommitmentExtractionResult`, `SourceMetadata`, and `EvidenceMetadata`. | **Yes** |
| **`requests`** | `>=2.31.0, <3.0.0` | Robust HTTP communication with Meta's chat completion endpoints (`POST /v1/chat/completions`). | **Yes** |
| **`pymupdf`** | `>=1.24.0` | High-speed, accurate text extraction from text-based and digital PDF documents with page number tracking. | **Yes** |
| **`Pillow`** | `>=10.0.0` | Image verification, decoding, and preprocessing for PNG/JPEG screenshot evidence. | **Yes** |
| **`rapidocr`** | `>=3.0.0` | Production in-Python OCR engine powered by `onnxruntime` for recognizing text in PNG and JPEG screenshots without requiring system Tesseract binaries. | **Yes** |
| **`pytest`** | `>=8.0.0, <9.0.0` | Standard test runner for running the test suite. (Built-in `unittest` also works out of the box). | Recommended |

---

## 3. Recommended Merge into Backend `requirements.txt`
Add the following lines to your backend `requirements.txt`:

```text
pydantic>=2.7.0,<3.0.0
requests>=2.31.0,<3.0.0
pymupdf>=1.24.0
Pillow>=10.0.0
rapidocr>=3.0.0
pytest>=8.0.0,<9.0.0
```

---

## 4. Environment Variables Required

| Environment Variable | Description | Default | Required in Production |
| :--- | :--- | :--- | :--- |
| `MODEL_API_KEY` | Bearer token / API Key for Meta Model API. | `None` | **Yes** (when using `MetaProvider`) |
| `META_BASE_URL` | Base URL for Meta Model API. | `https://api.meta.ai/v1` | No |
| `META_MODEL` | Meta model identifier. | `muse-spark-1.3` | No |
| `AI_PROVIDER` | AI provider selection (`"meta"` or `"mock"`). | Auto-detects (`"meta"` if `MODEL_API_KEY` present, else `"mock"`) | No |
