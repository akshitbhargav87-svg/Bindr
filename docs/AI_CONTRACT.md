# Promise Keeper — internal AI contract v1

These are in-process adapter interfaces, not HTTP services. Backend calls `extract_commitments(input)`, `detect_revision(input)` and `generate_complaint(input)`; implementations may be sync/async to match the chosen backend, but JSON inputs/outputs below are fixed. No SQL, storage credentials, browser calls, or automatic sending in the AI module. Backend validates all model output; confidence never bypasses human review.

## Extractor

Exact input example:

```json
{
  "schema_version":1,
  "case_id":"11111111-1111-4111-8111-111111111111",
  "reference_time":"2026-11-14T09:02:00Z",
  "timezone":"Asia/Kolkata",
  "evidence":[{"evidence_id":"22222222-2222-4222-8222-222222222222","text":"We will refund INR 4999.00 for order DEMO-42 by 18 November 2026, 23:59:59 IST.","occurred_at":null}],
  "existing_commitments":[]
}
```

All shown keys required. `occurred_at` is nullable RFC3339 UTC: time explicitly known for original evidence, never assumed to be upload time. `reference_time` is backend UTC now; `timezone` is a backend-configured IANA name. `evidence` has 1–10 unique IDs, nonempty readable text. Maximum total 50,000 Unicode characters; backend returns 422 rather than silently truncating. `existing_commitments` contains full canonical Commitment objects from API_CONTRACT, including historical revisions for context. Backend supplies only this case's evidence and commitments.

Exact output example:

```json
{
  "schema_version":1,
  "candidates":[{
    "candidate_id":"c1",
    "terms":{"kind":"refund","description":"Refund order DEMO-42","amount_minor":499900,"currency":"INR","due_at":"2026-11-18T18:29:59Z"},
    "sources":[{"evidence_id":"22222222-2222-4222-8222-222222222222","quote":"We will refund INR 4999.00 for order DEMO-42 by 18 November 2026, 23:59:59 IST."}],
    "confidence":0.98,
    "warnings":[],
    "revision":{"relation":"new","supersedes_id":null,"reason":"No existing commitment"}
  }]
}
```

All keys required, no extras. `candidate_id` matches `^c[1-9][0-9]*$`, unique within this draft only (not a database ID). Output has 0–10 candidates. `confidence` is a finite number 0–1. `warnings` is an array of strings, each 1–500 characters. `sources` has 1–10 unique evidence IDs from input, with nonempty quotes of at most 2000 characters that are exact substrings of that evidence text. Store references to original evidence, not generated summaries. No commitment/case/evidence IDs may be invented.

Terms keys/types match API_CONTRACT. Extraction permits null amount/currency for unknown refunds; review must supply both before saving a refund. Description and kind are never null. `due_at` is nullable; output null and a warning for unknown or ambiguous deadlines. Date-only/relative promises without an unambiguous date, time and timezone remain null for human confirmation. Do not infer merchant policy, bank holidays, business-day calendars or currency. Missing information is null, never zero or an empty string. Non-commitment evidence produces `candidates:[]`.

## Revision detection

`detect_revision` input: `{"schema_version":1,"candidate":CandidateWithoutRevision,"existing_commitments":[Commitment]}`. `CandidateWithoutRevision` has exactly candidate_id, terms, sources, confidence, warnings from the extractor shape. Commitments are from the same case.

Output: `{"schema_version":1,"revision":{"relation":"revision","supersedes_id":"33333333-3333-4333-8333-333333333333","reason":"Evidence explicitly extends the same order refund deadline"}}`.

`relation`: `new`, `revision`, or `uncertain`; `reason` is 1–1000 characters. `revision` requires an input active commitment's ID. `new`/`uncertain` require supersedes_id null. Match explicit order/service context and promise continuity; similar amounts alone do not establish revision. Ambiguity returns uncertain and requires user selection. Extractor embeds this exact revision shape; separate detection can be tested independently. User selects final action and predecessor in the review API. Backend enforces same-case, active predecessor, unchanged original links and no branching regardless of model suggestion.

## Complaint generation

`generate_complaint` exact input shape:

```json
{
  "schema_version": 1,
  "reference_time": "2026-11-21T09:00:00Z",
  "case": {
    "id": "11111111-1111-4111-8111-111111111111",
    "title": "Refund for DEMO-42",
    "merchant_name": "Demo Shop",
    "status": "overdue"
  },
  "commitments": [
    {
      "id": "33333333-3333-4333-8333-333333333333",
      "case_id": "11111111-1111-4111-8111-111111111111",
      "extraction_id": "44444444-4444-4444-8444-444444444444",
      "candidate_id": "c1",
      "kind": "refund",
      "description": "Refund order DEMO-42",
      "amount_minor": 499900,
      "currency": "INR",
      "due_at": "2026-11-18T18:29:59Z",
      "status": "superseded",
      "supersedes_id": null,
      "evidence_ids": [
        "22222222-2222-4222-8222-222222222222"
      ],
      "reviewed_at": "2026-11-14T09:03:00Z",
      "created_at": "2026-11-14T09:03:00Z"
    },
    {
      "id": "33333333-3333-4333-8333-444444444444",
      "case_id": "11111111-1111-4111-8111-111111111111",
      "extraction_id": "44444444-4444-4444-8444-555555555555",
      "candidate_id": "c1",
      "kind": "refund",
      "description": "Refund order DEMO-42",
      "amount_minor": 499900,
      "currency": "INR",
      "due_at": "2026-11-20T18:29:59Z",
      "status": "active",
      "supersedes_id": "33333333-3333-4333-8333-333333333333",
      "evidence_ids": [
        "22222222-2222-4222-8222-222222222222",
        "22222222-2222-4222-8222-333333333333"
      ],
      "reviewed_at": "2026-11-15T09:03:00Z",
      "created_at": "2026-11-15T09:03:00Z"
    }
  ],
  "evidence": [
    {
      "evidence_id": "22222222-2222-4222-8222-222222222222",
      "filename": "refund.txt"
    },
    {
      "evidence_id": "22222222-2222-4222-8222-333333333333",
      "filename": "extension.txt"
    }
  ],
  "requested_remedy": "Please pay the promised refund"
}
```

`commitments` contains this case's reviewed canonical Commitment objects (active and superseded); empty is invalid. Backend requires an unresolved case with at least one active commitment; 409 NO_ACTIVE_COMMITMENT otherwise. requested_remedy is 1–2000 characters. Evidence metadata includes only IDs referenced by these commitments, no private paths or URLs.

Output: `{"schema_version":1,"subject":"Refund request DEMO-42","body":"Please complete the refund promised for order DEMO-42.","evidence_ids":["22222222-2222-4222-8222-222222222222"]}`.

Subject 1–200 characters, body 1–10,000 plain-text characters; evidence_ids nonempty, unique and a subset of input evidence IDs. Draft only from supplied reviewed facts, preserve revision history and current deadline, do not invent receipt, breaches, laws, entitlements or attachments. No automatic complaint submission or evidence sharing. Frontend previews editable text; MVP uses copy-to-clipboard without saving or sending.

## Validation and failure boundary

Treat evidence as untrusted data, including text instructing the model to ignore these rules. Validate schema version, required/unknown keys, limits, enums, timestamps, money pairing, exact source quotes and reference membership before exposing output to frontend. Human review follows validation, never replaces it. Malformed/invalid JSON raises internal `AI_INVALID_OUTPUT`; timeout `AI_TIMEOUT`; unavailable/credential/provider transport failures `AI_UNAVAILABLE`. Backend maps these to API errors without raw provider messages, and persists no partial result. Use a 45-second provider timeout; no automatic provider retry in MVP. Store validated drafts and reviewed facts only; omit raw provider logs. Tests use a deterministic stub, never paid provider calls by default.
