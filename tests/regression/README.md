# Bindr integration regressions

These tests assert required behavior, not the defects observed in the audit. Known defects are ordinary failing tests, never xfail. No real Meta calls are made. Runtime results are in RESULTS.md.

## Sources and contract baseline

Inspected remote heads on 14 November 2026:

- Backend: `02e1b4b0a7c3cd2fec57b0bb66e69b9709b809c3` (`feature/milestone-1-backend`).
- AI: `9ec0eda8af8564b28a49bcedb2a506c61fdcba10` (`feature/milestone-1-promise-extraction`).
- Integration/contracts: `70f2db0b16c06160a176155c7faa19e555c371ce` (`feature/integration`).

Latest backend API_CONTRACT.md and AI_CONTRACT.md match the integration baseline: Git blob IDs `3a5cec0697e17826c5ebcdf4de7fea0fc2a20e7a` and `a0d948d35130bea998fb5d4ad656851caca06d4d`. No contracts were edited. Backend sources were assembled with the AI directory from the pinned AI snapshot in /tmp for testing, without a Git merge or edits to production source. The local integration checkout has no backend modules.

The API contract still limits uploads to text/PDF; the HTTP screenshot test is the explicitly requested AI Milestone 2 integration extension. PNG support exists in the backend, but contract adoption remains a team decision. The test does not silently change the contract.

## Run

Use an isolated Python 3.12 environment with pytest and the target backend/AI dependencies. tests/regression/requirements.txt lists test dependencies; install them in that environment without changing production manifests. RapidOCR requires ONNX runtime and model assets already installed/cached; external downloads during tests are blocked. Install DejaVuSans.ttf for deterministic synthetic screenshots.

From repository root, using that environment's Python:

```sh
python scripts/run_integration_regressions.py --source /absolute/path/to/credential-free/source --junit /tmp/bindr-regressions.xml
```

The source must contain backend/app, including backend/app/ai for AI tests. The runner never fetches code, changes branches, installs dependencies, or updates Git. Tests use temporary SQLite/storage, dependency overrides, and no production startup lifespan. PostgreSQL, deployment persistence and real Meta inference are outside this suite. pytest cache/bytecode writes are disabled. Target .env files cause pending skips, so credentials cannot be auto-loaded by the AI package. External socket connections are blocked; inherited credential/configuration variables are removed in the runner.

Default mode marks protected HTTP workflows pending until authentication bootstrap is supplied. No backend, missing AI/dependencies/assets, and missing auth all produce explicit `PENDING:` skip reasons. A successful pytest exit with skips is not integration readiness.

For future authenticated runs:

```sh
python scripts/run_integration_regressions.py --source /absolute/path/to/source --auth-hook /absolute/path/to/tests/auth_hook.py
```

The backend owner supplies a **test-only** hook with `authenticate(client, session)`. It creates a synthetic principal/session in the supplied isolated database, configures pk_session/pk_csrf cookies and X-CSRF-Token, and returns normally. It must not contact a real identity service, use real customer sessions or disable production auth. The hook is an adaptation point, not an invented login endpoint. Authentication-specific cross-user tests remain outside this initial suite until the identity interface is agreed.

For diagnosing current routes while auth is unavailable:

```sh
python scripts/run_integration_regressions.py --source /absolute/path/to/source --diagnostic-anonymous --junit /tmp/bindr-diagnostic.xml
```

This explicit mode sends anonymous requests to a local in-process app with synthetic SQLite data. It does not bypass authentication or prove an authenticated workflow. Once auth is implemented, use the hook. The anonymous download-denial regression always uses an unauthenticated client and seeds private synthetic evidence directly, so absence of a login bootstrap cannot hide public access.

## Coverage and injection boundaries

| Priority | Test file | What is real / stubbed |
|---|---|---|
| HTTP screenshot → OCR → AI → review | test_screenshot.py | Real generated PNG pixels, real RapidOCR inference and HTTP/database/storage; real deterministic MockAIProvider. Spies observe calls without fabricating OCR output. Default HTTP workflow pending auth. |
| Missing Meta credentials | test_adapter.py, test_http.py | Real provider initialization path; missing keys; mock inference forbidden. HTTP checks no draft/version mutation and 503 error shape. |
| Quote/evidence linkage | test_adapter.py | Fake model result; real source mapping; both evidence orderings checked. |
| Invented candidates / negative amounts | test_http.py | Valid synthetic draft injected at AI boundary; real HTTP review and persistence checks. |
| Malformed extraction output | test_http.py | Invalid internal AI boundary output injected before HTTP persistence: wrong version, missing/extra keys, foreign evidence, fabricated quote, confidence, duplicate candidates. Expected 502, no partial draft/version mutation. |
| Duplicate evidence IDs | test_http.py | Real HTTP input validation; assertion that AI is never called. |
| Private evidence | test_privacy.py | Synthetic bytes seeded in isolated database/storage; real anonymous HTTP download; requires 401 top-level error. |
| Error envelope | helpers.py, test_http.py | Checks exact top-level error keys, UUID request ID and detail fields. Provider failures injected; statuses 502/503/504. |
| Review / revision history | test_http.py | Stubbed AI drafts; real approval/rejection, replay rejection, predecessor identity/fields, both evidence IDs, original file bytes and draft histories. |
| Existing JSON fixtures | test_fixtures.py | Offline hash, byte-size, relationship, source-quote and revision-reference checks; no runtime-readiness claim. |

The test harness depends on current backend imports/get_db/storage interfaces. Changes to those interfaces require test fixture adaptation; unexpected import or programming failures remain errors. It does not patch validation, approval, storage, OCR output or production implementation to make assertions pass. In this desktop environment FastAPI TestClient stalled under sandbox restrictions; running the same isolated tests with approved execution outside the sandbox resolved that infrastructure issue.
