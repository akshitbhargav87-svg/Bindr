# Live Google Cloud acceptance — 15 November 2026 (IST)

**App:** https://bindr-404714938412.asia-south1.run.app

The user provisioned the Google project and deployed `main` at `0720daf` through the documented Cloud Build/Run script. The deployment output reported revision `bindr-00001-5t9` serving all traffic. Google Cloud credentials and the Meta key were entered by the user, not shared in chat.

The subsequent deployment used `c4ac921` and reported revision `bindr-00002-d9m` serving all traffic. The post-redeploy acceptance checks below passed on that service.

## Verified against the deployed service

| Check | Result |
|---|---|
| Homepage and direct `/app/cases` navigation | HTTP 200; production frontend loads |
| Real typed frontend adapter over HTTPS | Session → create → upload → Meta extraction → human approval → revision → complaint → original download → stale-write rejection → resolution passed |
| Actual PNG screenshot, without embedded text metadata | RapidOCR and the configured Meta provider produced a source-linked INR 150 refund suggestion; explicit review saved it |
| Private original bytes | PNG and text downloads exactly matched the uploaded bytes; PNG SHA-256 matched metadata |
| Browser workspace | A fresh workspace completed paste → live extraction → explicit amount/date review → confirm → case timeline; the saved case remained available after page refresh |
| Cookie security | Session cookie Secure and HttpOnly; CSRF cookie Secure |
| Anonymous original download | HTTP 401 |
| Another workspace's case and original download | HTTP 404 for each |
| Public health URL | `/health` returned HTTP 200 with `status=healthy` and `service=Bindr` after the follow-up deployment; the handler queries the real database |
| Records across redeploy | The pre-redeploy OCR case and its reviewed INR 150 commitment remained readable with the original private workspace cookie |
| Original across redeploy | Downloaded PNG matched both the original bytes and the SHA-256 recorded before redeployment |
| Direct public GCS access | Unauthenticated object URL returned HTTP 403 |

All uploaded evidence was synthetic. Production API behavior verifies the deployed app's access to its configured database and evidence storage; this is not an audit of every Google IAM or billing setting.

## Health URL correction

Google documents reserved URL paths, including some paths ending in `z`. The first deployment's `/healthz` startup probe worked internally, but public requests never reached the app. The follow-up adds the same real database query at `/health` and uses it in the deploy script, CI startup check and current guide. `/healthz` remains a compatibility alias for existing local/Render checks. See [Google's known issue](https://docs.cloud.google.com/run/docs/known-issues#reserved-url-paths).

## Deployment acceptance completed

The follow-up deployment passed public health, record persistence and exact-file persistence checks. Anonymous access to the preserved original still returned HTTP 401. The test cookie and file are retained privately outside Git; no session tokens are included in this report.

Lokesh's following three commits (`cad168e`, `ce26efc`, `4539aaf`) updated documentation and docstrings only. Comparing Python syntax trees with docstrings removed confirmed no executable changes in their five modified Python files. Those documentation updates do not require another deployment. The [migration audit](GOOGLE_CLOUD_MIGRATION.md) records the earlier 222 local tests and GitHub CI evidence. MVP limitations in the README continue to apply.
