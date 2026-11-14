# AI Module Dependencies (Milestone 1)

**Target Audience:** Backend Lead / Backend Developer  
**Location:** `backend/app/ai/`

---

## 1. Overview
In accordance with AI ownership rules, the shared root `requirements.txt` was not modified directly. The proposed dependencies below are required for the **Promise Extraction Engine (Milestone 1)**.

---

## 2. Dependency List & Justification

| Package | Recommended Version | Purpose | Is Required? |
| :--- | :--- | :--- | :--- |
| **`pydantic`** | `>=2.7.0, <3.0.0` | High-performance schema validation, data serialization, and contract enforcement for `CommitmentExtractionResult` and `SourceMetadata`. | **Yes** |
| **`requests`** | `>=2.31.0, <3.0.0` | Lightweight, robust HTTP communication with the Gemini REST API endpoints without heavy SDK overhead. | **Yes** |
| **`pytest`** | `>=8.0.0, <9.0.0` | Standard test runner for running the synthetic test suite. (Built-in `unittest` also works out of the box). | Recommended |
| **`google-genai`** | `>=0.1.0` | Official Google GenAI SDK. *Optional*: Current implementation uses direct REST API calls, so this is only needed if the team standardizes on the official client library. | Optional |

---

## 3. Recommended Merge into Backend `requirements.txt`
Add the following lines to your backend `requirements.txt`:

```text
pydantic>=2.7.0,<3.0.0
requests>=2.31.0,<3.0.0
pytest>=8.0.0,<9.0.0
```

---

## 4. Environment Variables Required

| Environment Variable | Description | Default | Required in Production |
| :--- | :--- | :--- | :--- |
| `GEMINI_API_KEY` | API Key for Google Generative AI / Gemini. (Alternatively, `GOOGLE_API_KEY` is also checked). | `None` | **Yes** (when using `GeminiProvider`) |
| `AI_PROVIDER` | Default AI provider selection (`"gemini"` or `"mock"`). | Auto-detects (`"gemini"` if key present, else `"mock"`) | No |
| `GEMINI_MODEL` | Gemini model name (e.g. `gemini-1.5-flash`, `gemini-1.5-pro`). | `gemini-1.5-flash` | No |
