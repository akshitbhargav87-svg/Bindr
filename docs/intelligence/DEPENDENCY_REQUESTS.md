# Track B dependency requests

15 November 2026. Runtime/root manifests remain A-owned and unchanged.

| Request | Why | Current behavior without it |
|---|---|---|
| Review and pin `extract-msg` with its transitive dependencies/license in A's runtime environment | `backend/app/ai/msg_import.py` implements bounded in-memory MSG body/header/attachment decoding using the documented bytes interface | Explicit recoverable decoder-unavailable error; EML/paste fallback. No package was installed or added to shared manifests. Real MSG sample acceptance is pending. |
| Select an approved transcription adapter/provider and tested language set | `ImportProcessor` accepts an injected `transcription(bytes,filename,timeout)` returning exact timed segments | Original/audio UI and segment fixtures are available; no fake transcript or provider call. |
| Supply a reviewed multilingual OCR handler/model if Hindi/Gujarati scans are advertised | Existing `DocumentProcessor` OCR injection is reused; text/citation transport fixtures preserve Hindi, Gujarati and Hinglish | Current native-language OCR quality is unverified. Default model assets do not establish these language claims. |

Current implementations reuse installed Pydantic, requests, PyMuPDF, Pillow and existing frontend packages. No root Python manifest, Dockerfile, deployment file or root CI file was edited. The owned `frontend/checks/ci-track-b.sh` is optional for A to incorporate.

Provider credentials must be configured through the existing secure environment/secret mechanisms, not pasted into chat or committed. No new paid-service activation was performed.
