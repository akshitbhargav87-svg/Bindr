# Google Cloud migration status

## Recovered task

The interrupted chat had already merged the integrated release into `main` at `69134f2`. Its final request was to switch hosting from Render to Google Cloud while retaining the current AI provider and leaving the actual cloud deployment to the user. The interrupted `deploy/google-cloud` branch had not been pushed. This continuation starts from the merged release in a separate `codex/google-cloud` checkout, preserving the existing frontend checkout and all contributor history.

## Delivered

- Cloud Run deployment script and Cloud Build configuration for the same-origin Docker app; 1 CPU, 2 GiB, one worker, low concurrency, scale-to-zero and an HTTP database startup probe.
- Private GCS storage selected with `EVIDENCE_STORAGE_BACKEND=gcs` and `EVIDENCE_GCS_BUCKET`. ADC uses the runtime service identity; no JSON key or public download URL is required. Local storage remains the default for development and the historical Render alternative.
- Create-only object uploads preserve originals; downloads are size-bounded and generation-checked. The API verifies ownership before accessing storage and keeps private/no-store download headers.
- Separate missing-file and temporary-storage errors, without leaking provider details. Blocking uploads run outside the event loop.
- Safe evidence compensation: a known pre-commit flush failure removes the object; an uncertain commit acknowledgement preserves it so a committed record cannot lose its original. SQL and GCS do not share a transaction; uncertain failures can leave an unreferenced private object requiring later administrative cleanup.
- Startup rejects Cloud Run configured with SQLite, local storage or a non-production environment. PostgreSQL connections are bounded to five per process without overflow.
- Cloud Shell guide for Cloud SQL PostgreSQL, private buckets, scoped runtime/build identities, Artifact Registry, Secret Manager and manual deployment. Provider/model defaults are retained and explicitly remain unverified with a live key.
- Updated README and deployment entry point; preserved the original Render guide and diagram images with current hosting annotations.
- Windows-compatible regression socket/font handling, while external network calls stay blocked, and LF shell-script rules for Docker/Cloud Shell.

## Verification in this continuation

Local runtime: Windows, Python 3.13.7, Node 22.17.0; pinned runtime requirements installed in an isolated virtual environment. The Docker/CI target remains Linux, Python 3.12 and Node 22.

| Check | Result |
|---|---|
| Backend and AI suite | **135 passed**, including 12 cloud-storage/configuration cases; real OCR runs with prepared models |
| Integration regressions | **28 passed**, no skips; signed sessions, no external provider calls |
| Frontend suite | **59 passed** |
| Connected production build | Passed |
| Real typed frontend adapter against local FastAPI/SQLite | Passed: session, create, upload, extract, review, revision, complaint, exact original download, stale-write rejection and resolution |
| Shell syntax and YAML parsing | Passed |
| PostgreSQL Unix-socket connection URL | Parsed by the actual psycopg dialect |
| Whitespace check | Passed |

Total: **222 tests**, plus the real-adapter lifecycle and production build. Cloud-storage tests use an in-memory GCS boundary: they establish application behavior, not live Google service/IAM behavior. Existing non-failing dependency deprecation warnings remain.

## Remaining live acceptance

No Google project was authenticated from this workstation; no cloud resources were created, no public URL is claimed and no paid AI request was made. The project screenshot and its ID were absent from the supplied transcript. Follow [the deployment guide](DEPLOYMENT_GOOGLE_CLOUD.md) using the actual project ID and enter provider credentials privately.

Before calling the deployment ready, verify Cloud Build, Cloud SQL startup, Google IAM and bucket permissions, HTTPS cookie behavior, real-provider extraction, another workspace's denied downloads, and record/original persistence across a redeploy. Add the verified URL and results here and in the README. The original release's [audit](RELEASE_AUDIT.md) remains historical evidence, not a claim of a deployed service.
