# Track B frontend

The existing capture/login remains available. New code uses the shared components/fonts/colors.

- `/app/capture-v2`: stable create/upload/extract/review operations, multiple proposals and manual-entry interface. Enable `VITE_ENABLE_V2_CAPTURE=true` only after A/B review the implemented profile and the actual v2 services exist. Disabled by default; fixture success never activates it.
- `/app/cases/:id/workflow`: real v2 snapshots, per-obligation balances/status, outcomes, revision review, questions, lifecycle/export/delete interfaces. Missing services show an unavailable state. No demo adapter is substituted.
- `/verify`: local, bounded SHA-256 manifest verification and a QR containing only the verifier URL. Files are not uploaded. Up to 512 MiB total/100 MiB per original, processed sequentially.
- `/app/share`: authenticated PWA POST-share review. The service worker keeps an incoming payload only in memory, binds it to the resulting client, expires it after ten minutes and consumes it once. Private APIs/evidence are never cached. A service-worker/process restart loses the pending handoff; upload/paste remains the fallback.

`CaptureProvider` is above the account-keyed route subtree. It keys drafts by verified account ID, hides them while signed out, invalidates old async writers and requires confirmation again after restoration. No sensitive drafts enter browser-persistent storage. Files must be reattached after a full tab/process loss. The optional cloud autosave controller requires the reviewed draft profile and the same flag above.

Provider-independent components exist for server-owned deadline previews, notification preferences/follow-up drafts, privacy/export/delete, reviewed sending/replies, audio-segment playback and sample-limited counters. A supplies the actual configured adapters/capabilities; the components do not guess provider-specific endpoints.

Run `npm run check`, `npm run check:track-b`, `npm run build`. Optional Linux CI entry point: `sh frontend/checks/ci-track-b.sh` from the repository root. `checks/fixtures` and `checks/browser-harness.mjs` are test-only and are not imported by app code. For the synthetic browser harness, build first, then run `node checks/browser-harness.mjs` from `frontend` and open its loopback URL. It does not use real identities/providers.

See `docs/intelligence/INTERFACE_V2_B.md` for the serialization profile awaiting joint integration review and `docs/intelligence/RETESTS_2026-11-15.md` for exact evidence/limits. No production provider acceptance is implied by a compiled disabled control.
