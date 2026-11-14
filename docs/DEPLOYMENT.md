# Deploy Bindr on Render

## Dashboard steps

1. Open the [Blueprint link](https://dashboard.render.com/blueprint/new?repo=https://github.com/akshitbhargav87-svg/Bindr).
2. Use **My Workspace** and branch **main**, Blueprint path **render.yaml**. Connect GitHub if prompted.
3. Review: one Docker web service (1 CPU / 2 GB), one PostgreSQL database (256 MB / 1 GB disk), and a 1 GB private evidence disk, all in Singapore. No separate static site, Redis, worker or external database is required.
4. Create/apply the Blueprint. `AUTH_SECRET` is generated, `DATABASE_URL` is wired privately, and the production frontend uses `/api/v1` on the same origin.
5. In the web service's **Environment** page, add **MODEL_API_KEY** with your real Meta Model API key. Confirm `META_MODEL=muse-spark-1.3` and `META_BASE_URL=https://api.meta.ai/v1` match your provider account. If your account uses a different model/endpoint, enter the actual values. Keep `AI_PROVIDER=meta`.
6. Choose **Save and deploy**. The build installs OCR weights; the first build may take several minutes. Watch the build and runtime logs until the deploy is **Live**.
7. Open the service's HTTPS URL. Test with a synthetic message, confirm it, reload, view original evidence, add/confirm a revision, generate a complaint and resolve the case.

Missing provider credentials produce an explicit error; they do not silently enable the offline extractor. `AI_PROVIDER=mock` is available only if you intentionally want an honestly labelled offline demonstration.

## Cost and operational boundaries

Current listed monthly infrastructure estimate: **$25 app + $6 PostgreSQL + $0.30 database storage + $0.25 evidence disk = $31.55**, before extra bandwidth/build usage and any provider charges. Render credits do not cover Meta's charges. Credits are a balance, not a spending cap; suspend paid resources when no longer needed. Pricing checked 14 Nov 2026; review the Dashboard estimate before applying.

The 512 MB app plan was rejected because OCR initialization alone measured roughly 529 MB peak locally. The 2 GB plan provides room for FastAPI and OCR. One process/instance is intentional; the private disk and in-memory abuse limiter do not support horizontal scaling. Attaching a disk causes brief deployment downtime. PostgreSQL metadata and original evidence have separate storage lifecycles; do not delete either resource expecting the other to restore it.

Use the generated secret consistently across restarts; rotating it invalidates workspace cookies. Browser access lasts up to 30 days, without account recovery. Do not place real sensitive documents in a judging demo.

## Updates and verification

Automatic service deployment is disabled in the Blueprint so unreviewed pushes do not replace a judging demo. Deploy the latest main commit manually after CI passes. Do not create a second Blueprint for routine updates; sync the existing Blueprint.

- `/healthz` must return healthy after a real database query.
- The homepage and `/app/cases` must load directly after refresh.
- Browser cookies must be Secure/HttpOnly for the session, with a readable CSRF cookie.
- Check an unknown workspace cannot read another workspace's case or evidence.
- Confirm original bytes survive a redeploy, and reviewed records survive page refresh.
- Run `node checks/live-api.mjs https://YOUR-SERVICE.onrender.com` from `frontend/` for the typed adapter lifecycle against the deployed origin. It creates synthetic test records and invokes the configured extractor.

Local tests do not establish production database behavior, external-provider availability or the final Render build. Record those results in RELEASE_AUDIT.md once the service is live.
