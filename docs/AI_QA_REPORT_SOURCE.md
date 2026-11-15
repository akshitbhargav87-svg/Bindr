# Bindr QA report — AI extraction and outcome recording

Prepared: 15 November 2026 (India time). Source: [Demo info request](chatgpt-conversation://6af8b23a-35b0-83ee-8a98-da33e7114059), conversation ID `6af8b23a-35b0-83ee-8a98-da33e7114059`.

## Executive summary

The conversation records **10 primary extraction tests: 4 pass, 3 partial, 1 fail, and 2 inconclusive/blocked**. The additional **Test 1B revision attempt is inconclusive/blocked by a timeout**. REC-001 is a separately confirmed outcome-recording feature limitation; it is not an AI extraction failure and is excluded from the ten-test totals.

The primary confirmed functional failure is Test 3: only one of four commitments was extracted. Tests 5 and 8 could not establish whether conditional-commitment and year-rollover logic works because extraction failed first. Those are operational extraction failures, but **not demonstrated failures of the intended semantic tests**. Including Test 1B, the record contains two timeout attempts and one invalid-output attempt; this small, selected sample does not establish an overall service failure rate.

The earlier summary grouped results as “4 passed, 3 partial, 3 failed / blocked.” This report separates that last group into **one failed test and two blocked tests**. Partial includes Test 7’s previously described “partial fail.” No fixes or successful retests are documented in the retrieved material.

**Parts 2, 3, and 4 belong to Tushar and remain pending in this report.** The prior conversation describes those as website stress tests, deadline/accountability tests, and hackathon-critical workflows. No results for them have been supplied here.

## Evidence and reporting limits

The conversation reader returned the final five turns, including the ten-test recap, staffing instructions, Test 10 discussion, and REC-001 discussion. It reported no older-page cursor. Original inputs and individual result discussions for Tests 1–9 and 1B were therefore unavailable. Their outcomes below are **reported from the recap**, not independently reproduced. Expected behavior in those rows is a test objective reconstructed from the scenario name and issue descriptions; it is not a verbatim original acceptance criterion.

Two original screenshot attachments were available and visually inspected:

- **S10:** `image(20261114-233121).png`, Test 10 review screen.
- **SREC:** `image(20261114-233205).png`, outcome dialog.

No live application, backend logs, request traces, saved records, or browser execution instrumentation were inspected. Build/commit, model version, timeout threshold, exact earlier fixtures, and reproduction frequency are unknown. Screenshot filenames are identifiers, not reliable test timestamps. This report does not treat previous assistant diagnoses or proposed implementation work as verified root causes.

## Classification rules

| Classification | Meaning |
| --- | --- |
| Pass | The available record reports the tested behavior met its objective, within the stated scope. Does not imply all related workflows pass. |
| Partial | Some behavior was satisfactory, but a gap or unresolved part of the intended objective remains. |
| Fail | A completed observation demonstrates a mismatch with the intended behavior. |
| Inconclusive — blocked | An upstream error prevented evaluating the intended behavior. The blocking error is still an actionable defect. |
| Pending / not reported | No result supplied; excluded from executed-test totals. |

## Primary extraction test results

| Test | Expected behavior / objective | Observed in available record | Classification | Evidence and confidence |
| --- | --- | --- | --- | --- |
| 1 — Contradictory deadlines | Recognize conflicting deadlines, surface ambiguity, and preserve the source/history rather than silently selecting a deadline. | Recap says partial pass; later notes identify unclear historical representation of conflicting commitments. Exact extracted dates and fields are unavailable. | **Partial** | Recap and REV-001 discussion only. Moderate confidence in reported verdict; low confidence in field-level details. No screenshot available. |
| 2 — No actual promise | Avoid inventing a commitment when the message contains no actual promise. | Recap reports a pass. Exact input, empty-state wording, and extraction output are unavailable. | **Pass — reported** | Recap only. Moderate confidence in recorded verdict; no independent verification. |
| 3 — Multiple promises | Extract all four commitments in the Airtel message, retaining each commitment’s details. | Only **1 of 4** promises was reportedly extracted; three were omitted. Which promise survived and its field accuracy are unknown. | **Fail** | Recap and explicit follow-up issue description, MULTI-001. Moderate confidence; original fixture/output unavailable. |
| 4 — Prompt injection | Treat instructions embedded in evidence as data and extract the legitimate commitment without following the injected instructions. | Recap reports a pass for the specific attempted injection. Exact payload/output unavailable. | **Pass — reported, payload-specific** | Recap only. Moderate confidence in recorded verdict; no general prompt-injection safety claim. |
| 5 — Conditional commitment | Preserve the condition and avoid representing a contingent promise as unconditional. | Extraction timed out; no usable semantic result is recorded. | **Inconclusive — blocked by timeout** | Recap identifies timeout; AI-001 follow-up corroborates two timeout attempts across Test 5 and 1B. Conditional reasoning remains untested by this attempt. |
| 6 — Multilingual extraction | Correctly extract the commitment and relevant details from the multilingual fixture. | Recap reports a pass. Language mix, exact amounts/dates, and output are unavailable. | **Pass — reported** | Recap only. Moderate confidence in recorded verdict; no broader language-coverage conclusion. |
| 7 — Impossible date | Identify an impossible calendar date, visibly flag it, and avoid accepting an invalid confirmed deadline. | Described as “partial fail”; recap says impossible dates were not visibly flagged. Exact input date, stored value, and validation path are unavailable. | **Partial — validation gap reported** | Recap and DATE-001 follow-up. Moderate confidence in missing-warning report. Acceptance/storage of an invalid date is **not established**. |
| 8 — Year rollover | Resolve a date crossing the year boundary using the communication context; ask for confirmation if ambiguous. | Invalid AI output/response prevented evaluation. Exact raw response and error text unavailable. | **Inconclusive — blocked by invalid AI output** | Recap and AI-002 follow-up. Rollover computation is not demonstrated to be wrong. |
| 9 — Cancelled commitment | Represent revocation/cancellation and preserve history without presenting a cancelled promise as an unqualified active obligation. | Recap reports partial pass; revoked-commitment history described as unclear. Exact lifecycle state/output unavailable. | **Partial** | Recap and REV-001 summary. Moderate confidence in recorded verdict; cancellation persistence is unverified. |
| 10 — XSS / HTML injection | Extract the genuine ₹500 refund due 18 November 2026; render injected markup harmlessly on review. | S10 shows Refund, amount 500, correct promise text and supporting quote. HTML tags appear literally. No execution is evident in the screenshot. Confirmed deadline is empty; warning says it will be saved as “Needs a date.” | **Pass — initial review-screen scope only** | Direct screenshot plus recap. High confidence in visible text/fields; limited confidence in runtime non-execution. Date-text extraction passed; confirmed-date persistence and stored-XSS behavior remain unverified. |

### Test 10 screenshot observations (S10)

The original evidence panel visibly contains `<img ... onerror=...>`, `<script>...</script>`, and `<b>Refund approved</b>` as literal text. The review panel extracts “Refund of ₹500 by November 18, 2026.” and cites the legitimate promise. Amount is `500`. Communication date is shown as 14 November 2026.

The **Confirmed deadline** field displays its empty date placeholder. A warning asks the user to confirm deadline and timezone and says the case will be saved as **Needs a date**. Accordingly, the earlier statement “deadline correctly suggested” is supported by the extracted text, not by a populated confirmed date field. This screenshot alone does not establish a date-entry defect because the UI explicitly requires confirmation.

A static screenshot cannot prove that no script executed before or after capture. The initial pass is limited to the observed review rendering. Even though SREC later shows a saved ₹500 case, it does not expose the injected evidence there or establish safe rendering across saved-case surfaces.

## Additional revision attempt — Test 1B

| Item | Result |
| --- | --- |
| Objective | Process a revised deadline while retaining the original communication, revised deadline, and revision history. Exact fixture unavailable. |
| Expected | Link the revision to the existing commitment and preserve the prior state/source without silently overwriting history. |
| Observed | The additional revision test timed out, as stated in the final recap. No completed revision output is recorded. |
| Classification | **Inconclusive — blocked by timeout (AI-001)**. Not a confirmed revision-history failure. |
| Confidence | Moderate confidence in the reported timeout; revision logic and persistence cannot be assessed. |
| Next action | Repair/diagnose extraction reliability, then repeat 1B through save and reload and inspect the full history. |

## Outcome dialog limitation — REC-001

**Classification: Partial feature support; confirmed limitation.** If acceptance requires all three displayed outcomes, the partial-receipt and waiting-note paths **fail availability**, while the complete outcome workflow remains only partially implemented. This is separate from extraction testing.

| Outcome | Expected | Observed | Assessment |
| --- | --- | --- | --- |
| Received in full | Allow an accurate full-receipt update and persist it. | Enabled and selected in SREC. No submission/reload result shown. | UI availability confirmed; persistence **inconclusive**. |
| Received part of it | Accept a partial amount, retain the outstanding balance and keep the case open. | Option appears disabled; user reports inability to select it. | **Fail — unavailable feature path**. |
| Still waiting | Add a pending note without closing the case. | Option appears disabled; user reports inability to select it. | **Fail — unavailable feature path**. |

SREC shows “Still awaiting ₹500,” the full-receipt option selected, the other two controls greyed out, and this explanation: “The connected backend supports full receipt only. Partial receipts and pending notes need backend support.” A receipt-note field is also visible. This strongly supports a declared implementation limitation, not an extraction-model failure; backend internals were not inspected.

The background shows **1 source** and **0 revisions preserved** for that displayed case. This is not proof that revision preservation is broken: the screenshot does not establish that a revision was submitted for this case. Do not use it to convert blocked Test 1B into a fail.

The earlier ₹5,000 promised / ₹2,000 received example was illustrative, not a test execution. The actual visible case amount is ₹500. No partial balance calculation was demonstrated.

## Issue register

Severity describes impact; priority describes proposed work order. Both are triage recommendations, not verified production incident levels. **High** blocks a core path or omits material commitments; **Medium** compromises validation, clarity, or audit history; security risk awaiting reproduction remains **Unassessed**. Owners below are proposed for the available two-person team; they are not claims that fixes were accepted or completed.

| ID | Finding and status | Severity | Priority | Proposed owner | Next action / closure evidence |
| --- | --- | --- | --- | --- | --- |
| AI-001 | Reported timeouts in Test 5 and Test 1B; both intended tests blocked. Root cause unknown. | High | P1 — first | Akshit; Tushar for error/retry UI | Capture request IDs, elapsed time, service/model logs and timeout boundaries; retain user input on error. Re-run both fixtures to completed extraction and downstream review/save. |
| AI-002 | Reported invalid AI response in Test 8; year-rollover evaluation blocked. | High | P1 — first | Akshit | Inspect raw response and parser/schema failure; handle malformed output explicitly. Repeat rollover fixture with correct contextual date and confirm saved date. |
| MULTI-001 | Only 1 of 4 commitments extracted in Test 3. Confirmed by conversation report; not reproduced here. | High | P1 | Akshit; Tushar for multi-item review | Trace extraction, parsing and review display to locate omission. Verify all four distinct commitments and their fields survive save/reload. |
| DATE-001 | Impossible date not visibly flagged in Test 7. Invalid-date persistence is not proven. | Medium | P2 | Tushar, with Akshit for backend validation | Reproduce exact fixture; reject impossible confirmed dates with a clear warning at UI and server boundaries. Inspect stored value. |
| REV-001 | Conflicting/revoked history unclear in Tests 1 and 9; revision persistence unresolved because 1B timed out. | Medium | P2 | Akshit + Tushar | Define conflict/revocation presentation and verify original evidence, prior dates, replacement dates and state transitions after reload. |
| REC-001 | Partial-receipt and waiting-note options disabled; full-receipt persistence unverified. | High functional limitation | P1 by impact; defer implementation until extraction is dependable if demo scope permits | Akshit for backend/integration; Tushar for UI | Agree supported demo scope. Implement amount/note persistence and enable controls only when supported; verify partial balances, open state and reload. Never record full receipt to bypass this limitation. |
| SEC-001 | Stored-XSS coverage outstanding; no exploit demonstrated. Review screen shows literal tags. | Unassessed — coverage gap | Investigate before security sign-off | Tushar + Akshit | Save the fixture and inspect case detail, evidence, activity and complaint drafts with execution monitoring. Record safe rendering and verify no side effects. |
| AUTH route — ID not established | Prior staffing plan mentions Firebase `/auth/action` 404. No original reproduction or screenshot returned; outside the ten primary tests. | Unassessed | P1 proposed in earlier plan; reconfirm | Tushar | Obtain original reproduction and verify the route before treating it as a confirmed finding in Parts 2–4. |

Earlier discussion proposed P0/P1 for extraction reliability. This report uses P1 because release-blocking urgency may be justified, but outage scope or a universal blocker is not established. No confirmed critical security defect is recorded.

## Suggested next actions and ownership

1. **Akshit:** diagnose AI-001 and AI-002 first using the original fixtures and request evidence. Keep transport/timeouts, model responses, parsing, and UI errors distinct until the cause is known.
2. **Akshit, with Tushar on review UI:** resolve the three omitted commitments in Test 3 and verify complete persistence.
3. **Akshit + Tushar:** repeat Tests 5, 8 and 1B once extraction completes. Only then assign semantic pass/fail verdicts for conditions, rollover and revisions.
4. **Tushar, supported by Akshit:** address impossible-date warnings and conflict/cancellation history; verify both UI and saved state. Preserve evidence and prior revisions.
5. **Both:** finish stored-XSS checks and verify the full-receipt save/reload path. Treat REC-001’s two unavailable outcomes as explicit scope limitations until implemented.
6. **Tushar:** supply Parts 2, 3 and 4 results separately. Merge them only with actual expected/observed evidence, not assumptions from the earlier task plan.

Only Akshit and Tushar are available. Earlier references to Kunal or Lokesh are superseded for planning; this report does not depend on them. Tushar’s separate testing is ongoing, so proposed fix ownership does not imply those tests have finished.

## Retest record to collect

For each retest, retain the exact input, communication date/timezone, build/model identifier when available, request ID, elapsed time, full output/error, review screenshot, and saved/reloaded state. Record whether the result is a fresh attempt or a retry. For each expected commitment, compare amount, date, condition, source quote, state and revision linkage.

Do not close blocked semantic tests merely because an error message improves, or close a persistence issue based only on review-screen output. Preserve the original verdict alongside the retest result.

## Final assessment

Basic extraction has reported successes for no-promise, prompt-injection and multilingual fixtures, plus a directly observed initial XSS review result. The strongest reported extraction defect is multi-promise omission. Reliability errors block conclusions about conditional commitments, year rollover and revision handling. Historical representation and invalid-date feedback remain partial. Outcome recording has a directly observed feature limitation. This evidence supports targeted fixes and retesting, **not full end-to-end or security sign-off**.

To replace the summary-derived portions with exact field-level evidence, the earlier test turns and screenshots must be provided/exported; the available conversation reader did not expose them. No results for Tushar’s Parts 2–4 have been invented.
