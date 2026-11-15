# Track B implementation profile v1

This owned document materializes the frozen parallel contract for independent tests. It does **not** revise `PARALLEL_IMPLEMENTATION_CONTRACT.md`, prove deployed endpoints exist, or authorize A/B to change shared names without review. Field details absent from the planning contract need joint review before activation.

**Combined integration update:** A's concrete `ba2e389` profile is now the wire format used by application pages through `frontend/src/api/platform.ts`, and by `services/intelligence/platform_profile.py` at the pure-engine boundary. The original B fixture/presentation profile below remains for historical independent tests. The platform adapter explicitly converts reviews to `action/edited_terms/predecessor_id`, mutations to `case_version`, drafts to `capture`, temporal/condition fields to A's published names, audio milliseconds to seconds, and ledger currency buckets to presentation rows. No server arithmetic or currency total is recomputed by that mapping. See `COMBINED_MVP_STATUS.md` for actual integration evidence and remaining limits.

## Python seam

```python
from backend.app.services.ai_adapter import ai_adapter
proposal = ai_adapter.extract_proposals_v2(request, diagnostics=diagnostics)
```

`provider=` is an explicit injection for controlled tests/approved adapters. The default resolves the existing configured provider; it never switches to synthetic output. The seam accepts data only. A must authorize every case/evidence/predecessor before calling it.

Request schema lives in `services/intelligence/contracts.py`:

- `schema_version:2`, `case_id`, safe `request_id`, `timeout_seconds` (1–90, default 30).
- `evidence`: 1–10 objects with `evidence_id`, bounded `segments`, and exact communication metadata from the frozen contract.
- Each segment has `text` and optional `page`, `message_id`, `start_ms`, `end_ms`. Both audio offsets are required together and ordered. A quote/location must match the same segment exactly.
- `existing_obligations`: current authorized records with unique `id`; optional `case_id`, `terms` and `communication`. Cross-case supplied context is rejected. Evidence and predecessor context each have a 50,000-character budget.

The returned proposal uses the frozen v2 candidate fields. `temporal` has `wording/anchor/duration/range/parse_status`; `condition` has `trigger/status`; `relation` has `kind/predecessor_id/explanation`. Candidate IDs and proposal ID are deterministic digests of validated content. Exact duplicates are reported and deduplicated; distinct obligations remain distinct.

`IntelligenceFailure` exposes `code`, `stage`, `request_id`, `retryable`. A maps that into the shared error envelope/job state. Codes are `VALIDATION_ERROR`, `AI_TIMEOUT`, `AI_INVALID_OUTPUT`, `AI_UNAVAILABLE`. No source bodies, credential strings, raw provider exception text or fabricated fallback success are logged/returned. `diagnostics` contains only stage/request ID/duration. Retry is explicit; there is one provider attempt per operation/document. A still owns durable job cancellation and process-level resource/HTTP deadlines; a Python callback or native parser cannot be forcibly interrupted by a post-return elapsed-time check.

`ImportProcessor.process(bytes, filename)` returns segments, claimed headers, separately bounded attachment bytes and warnings without storage writes. A retains the original and authorizes/quotas attachment ingestion. Inject `DocumentProcessor(ocr_handler=...)`, approved MSG parsing or transcription deliberately. These processors do not fetch remote HTML resources.

## Frontend serialization profile

`src/api/v2.ts` supplies strict decoders and credentialed, no-store requests with `X-Bindr-Account`, CSRF and stable `Idempotency-Key`. Mutations are never auto-retried. The same key/body remains available after timeout/network uncertainty; changed content and another account cannot reuse it. Requests have a 45-second client abort; abort leaves uncertainty, not a declaration that no server write occurred.

Operation replay/cache is also scoped to the HTTP method and exact case/action path. CSRF selection prefers the host/account cookie over the legacy cookie. A 401 clears account identity even when its body is not JSON. Extraction envelopes are decoded before caching success; an explicit `case_version` is preserved for subsequent review. This field remains part of the profile to review with A, not an assumed version inferred by B.

The independent fixture server is under `frontend/checks/fixtures/`, imported only by tests. It is synthetic, process-local, and cannot count as production persistence, authorization, provider delivery or PostgreSQL concurrency acceptance.

Concrete core profiles used by B:

- Create: `{title,merchant_name}`; result `{id,version}` or `{case:{id,version,...}}`.
- Evidence: multipart original file, `expected_version`, JSON `communication`. Operation fingerprint includes original SHA-256, filename, size, version and metadata. Result `{evidence:{id,...},case_version,duplicate_of}`. Matching originals are reviewed, not silently duplicated in extraction IDs.
- Extractions: `{evidence_ids,expected_version}`; completed `Proposal` or `{proposal,...}`, otherwise a job envelope. An already queued operation is not resubmitted automatically.
- Reviews: `{expected_version,proposal_id,decisions:[{candidate_id,selected,terms,predecessor_ids,deadline_override?,reason?}]}`. Overrides use `{date,timezone,precision:'date'}`. Snapshot-returning review/outcome mutations are strictly decoded. A must explicitly define whether unselected candidates close or remain reviewable; the UI only promises that they are not confirmed/included in totals.
- Manual promise: `{expected_version,terms,source_ids,origin}`; `origin` is `source_backed` or `user_attested`. There is no invented extraction/quotation.
- Outcomes: `{expected_version,kind,allocations:[{obligation_id,amount_minor,currency}],received_at,note,source_ids}`. Pending/company claims carry no receipt amounts. A validates ledger/correction/full-resolution rules transactionally.
- Capture draft create/update: `{expected_version,text,metadata:{company,title,communicationDate},source_references}`; response `{id,version,text,metadata,source_references}`. Autosaves serialize and retain uncertain operations for exact replay. No browser-persistent draft storage is used.
- Case snapshot: `{id,version,obligations,events,projection:{status,money_by_currency,as_of,timezone},capabilities}`. Obligation terms/status/balance/outcomes are independent; client time never determines overdue/balance.
- Job: `{id,status,stage,retryable,request_id,resource_id?,version?,error?}`. Allowed states match the frozen contract. Queued-job proposal retrieval details are still required from A; B does not invent a GET proposal route.

These are the B fixture profile's concrete field names. Review them against A's implementation before enabling the new UI. `capabilities` names (`reviews/outcomes/exports/calendar/lifecycle/delete/questions`) are fixture profile labels pending the same review, not a new claim about deployed server flags.

## Activation and remaining subcontracts

- Existing v1 capture/login remains available. `/app/capture-v2` and cloud capture autosave require `VITE_ENABLE_V2_CAPTURE=true` **after** the shared profile is reviewed and the actual server is ready. The default is disabled.
- `/app/cases/:id/workflow` requires an actual authenticated v2 snapshot; a missing endpoint produces an honest unavailable state. Fixture modules are not imported by that page.
- `/verify` computes original-file digests locally, with bounded sequential memory use. The QR contains the public verifier URL only, no private case reference.
- `DeadlineReview`, `WorkflowPreferences`, `PrivacyControls`, `ConnectionReview`, `AggregateCounter` and `AudioSegment` are provider-independent components. Their adapters/capabilities must come from A's reviewed services. Unconfigured connections/sends are disabled.
- Provider-specific connector URLs/scopes, encrypted credential custody, pairing token lifetime, reviewed-send payload/receipt and reply-intake contracts belong to A. B has not guessed those routes.
- A must supply actual calendar ID/version, export snapshot/download/retention profiles, capture-draft discovery/restoration locator and job-to-proposal retrieval. Cloud draft IDs remain in memory; a full tab loss cannot discover an unsaved/local draft or restore unattached files magically.
