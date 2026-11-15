# Combined MVP integration — 15 November 2026

**Integration is implemented and exercised locally; deployment is not approved.** This report separates actual A+B code integration from real-model, browser, cloud and provider acceptance.

## Pinned sources and preservation

- Track A: `ba2e3894a367d1a3f6470a6d64e90af8a8d366c1`, `origin/codex/platform-reliability`.
- Starting Track B: `bf79db9b719c98a0e1f422c261061d7a10a7fe02`; subsequent compatibility fixes are committed on `codex/intelligence-product` and merged into the separate integration branch.
- Combined worktree: `../bindr-integration`, branch `codex/qa-integration`. Both account-aware histories are retained, descending from account head `888722d`.
- The initial merge conflicted only in two source handoff documents. The frozen ZIP copies were kept at their shared paths; Track A's conflicting copies were preserved verbatim under `docs/intelligence/integration-source-copies/` on integration. Original QA verdicts were not rewritten.
- No A runtime/service/schema/test implementation was edited by B. A-owned corrections below remain requests. No production deployment, migration, private evidence upload, external correspondence or provider activation occurred.

## Connected changes

1. Added `services/intelligence/platform_profile.py` to adapt A's authorized `text/pages/communication/context` request into B's strict bounded segment schema, and return A's published Temporal/Condition/audio-offset profile. Each new extraction operation has a distinct proposal identity; exact replay remains stable.
2. Exposed the real `answer_case_v2` seam over A's already authorized source snapshot, returning verified citation IDs and abstention. No tools or unauthorized retrieval are added.
3. Added `frontend/src/api/platform.ts` to map the published A wire profile into B's presentation types. It connects actual reviews, manual attestation, receipts, case snapshots, extraction versions, draft autosave, jobs, grounded answers, exports/deletion and private authenticated downloads. No fallback to the independent fixture backend exists in application code.
4. Wired the enabled v2 workspace/capture UI, per-obligation balances and explicit legacy-v1 separation. Receipt time is user-entered with offset. Date-only overrides remain dates; an exact time is confirmed explicitly, not invented as midnight. Cancellation/corroboration requires an active predecessor and explicit review.
5. Added selected-original export controls and correct download format names. Reminders stay visibly unavailable pending managed scheduling and delivery acceptance. Existing v1 complaint drafting is labeled as the legacy view; v2 facts are not silently represented by an old v1 draft.
6. `VITE_ENABLE_V2_CAPTURE=true` was used only for integration builds. No root Docker/deployment configuration or deployed frontend flag was changed. The flag must be reviewed with A at release.

## Fresh verification

| Check | Result | Boundary |
|---|---|---|
| Combined backend/AI suite | **296 passed, 2 failed**, 3 subtests passed, 6 deprecation warnings; 47.49s | Failures below are retained, not skipped or rewritten. All new combined core tests pass. |
| New combined core tests | **4 pass**, included in the suite above | Real A HTTP/SQL + B adapter/validators/answer engine; controlled synthetic inference provider only. All four Airtel candidates, subset review, individual source/date/money persistence, partial receipt, revision, answer and bundle bytes. |
| Preserved integration regressions | **28 passed**, 2 deprecation warnings; 23.20s | Existing assertions unchanged; real local OCR and explicit mock inference. |
| Existing frontend suite | **81 passed** | Run on combined source. |
| Track B frontend suite | **21 passed** | Includes actual component fixture flows, account recovery, stored markup and transport/profile tests. |
| Actual React capture -> combined real HTTP server | **2 passed** | Mounted actual React capture/review component, real A routes/SQLite/original storage and B client/seam. Normal save and response-lost-after-upload paths produce one obligation; exact retry keeps the key. JSDOM is not a full browser. |
| Actual frontend PlatformClient -> real combined server | **PASS** | Session/create/original upload/extraction/review/₹200 partial receipt/₹300 outstanding/cited answer/cloud draft/private bundle download. Bundle was 265,472 bytes in the recorded run; no public URL. |
| TypeScript/Vite connected build | **PASS** | `VITE_USE_MOCK=false`, `VITE_ENABLE_V2_CAPTURE=true`, existing API root. No deployment. |
| Browser attempt | **Unavailable** | Browser tool reported local browser access unavailable in this chat. No real-browser acceptance or screenshot was fabricated. |

The explicitly opt-in QA server is `frontend/checks/combined-server.py --synthetic-inference`. It refuses non-development/non-anonymous configuration and binds to loopback. Its test-only export-processing route exists only in that runner, not the production app. It uses separate ignored synthetic SQLite/evidence storage. The paid inference call alone is controlled; there is no silent production mock.

To repeat connected client checks from `frontend` while the explicit QA server runs:

```text
node checks/combined-http.mjs http://127.0.0.1:8033
set BINDR_COMBINED_QA_ORIGIN=http://127.0.0.1:8033
node --test checks/capture-v2-flow.test.mjs
```

Python dependencies added by A were installed in an integration-only package directory. The existing reference virtual environment, dependency manifests and dirty reference worktree were preserved.

## Remaining A-owned findings

1. `test_missing_v2_engine_is_a_typed_failure_not_mock_success` expects `INTELLIGENCE_V2_UNAVAILABLE` because it was authored before the real seam existed. With the connected seam and no model credential it correctly refuses inference with HTTP 503, but code is `AI_UNAVAILABLE`. A should update the missing-method test to inject an object without the method, and separately test an unconfigured connected provider. Keep the no-fabricated-output/no-facts assertion.
2. `test_rfc3161_checks_chain_nonce_and_digest` fails when Windows OpenSSL executes the synthetic timestamp response command. External timestamps remain disabled/deferred. This is not an established failure of a real timestamp authority; Linux/container reproduction and stderr diagnosis belong to A. No broad timestamp claim is made.
3. `services/platform/intelligence_boundary.invoke` converts every engine exception to generic `AI_UNAVAILABLE`, losing B's typed timeout/invalid-output code. A should map safe allowlisted `IntelligenceFailure` fields while preserving redaction and the late-result/no-write boundary. Do not expose raw model errors or evidence.
4. Notes/transcripts, email/audio extraction dispatch, general asynchronous long-document processing, credential-key rotation and distributed abuse controls remain as stated in A's handoff. Keep their unsupported product paths disabled; do not infer completion from this core test.

## MVP decision and release gates

The user prioritized a dependable MVP rather than optional expansion. Deferred: extension pairing/publishing, WhatsApp media, advanced audio, public scoreboard/moderation, external timestamps and broader escalation routes. Existing implementations/adapters remain in source, with unsupported production actions disabled.

Required before deployment:

- Configure the existing real Meta provider securely and repeat all ten canonical cases + dated 1B through the connected review/save/reload journey. No model credential was available in this environment and no real Meta success is claimed.
- Real-browser v2 acceptance: full journey, stored-XSS across saved surfaces, two-tab conflicts, stale complaint handling and responsive layout. Controlled real Firebase verification/reset/reuse/MFA and same/different-account/cross-device recovery remain explicit gates.
- Rehearse Cloud SQL additive schema-11 migration on restored data, preserve existing account sessions/cases/original hashes, validate backup restore and rollback/image pairing. New production startup refuses a stale schema; deploying without migration rehearsal can prevent startup.
- Build/test the actual container and combined CI. A's PostgreSQL evidence was local to his environment; no fresh simultaneous PostgreSQL test was run on this Windows host.
- Choose whether reminders/automatic cleanup are included. If included, configure authenticated managed worker scheduling and verify real controlled delivery/cancellation. If reminders are excluded, keep them visibly unavailable; still establish export/deletion cleanup and actual retention behavior before claiming those workflows are production-ready.

Deployment remains the last reviewed step after these gates. No final merge, cloud rollout or external message send was performed.
