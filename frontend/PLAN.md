# Bindr build plan — 14 Nov 2026

1. Repository: local `bindr-app`, downloaded from main @ 870f244; no frontend branch published.
2. Reference contracts: downloaded unchanged from feature/integration @ 70f2db0 into sibling docs/.
3. All implementation changes stay inside frontend/. Existing design workspace remains read-only.
4. Routes: `/` marketing; `/app` overview; `/app/cases` list; `/app/cases/:id` case detail.
5. Further routes: `/app/upload`, `/app/review/:id`, `/app/cases/:id/complaint`, `/app/evidence`, `/app/settings`.
6. Phase 1 reserves `/app/*` with an explicit build-checkpoint screen; it does not pretend capture works.
7. Structure: src/pages, src/components, src/api/{types,http,mock,mapper,index}, public/.
8. API: exact /api/v1 cases, detail, file upload/download, extraction, review, resolve, complaint-draft routes.
9. Contract objects use UUIDs, snake_case, integer minor-unit money and optimistic expected_version.
10. HTTP carries credentials and CSRF; never auto-retries mutations. Review remains explicit.
11. GAP: sessions required by contracts, bootstrap undefined. No login UI added; mock is the default.
12. GAP: contract only accepts UTF-8 text and text-layer PDF; screenshot OCR is not supported.
13. GAP: no partial outcome, reopen, edit, archive, restore, delete, manual commitment or duplicate API.
14. GAP: no evidence communication-date upload field, deterministic calendar result, agenda, inbox, settings or saved-draft API.
15. Phase 1: React/Vite/Tailwind, fonts, tokens, primitives, routing, adapter boundary, landing.
16. Phase 2: shell, dashboard, cases and offline/error views.
17. Phase 3: capture, extraction, confirmation and recovery paths.
18. Phase 4: detail, original/revised source-linked timeline and supported outcome actions.
19. Phase 5: editable complaint draft, review and copy/export.
20. Phase 6: agenda/settings and accessibility/mobile polish.
21. Phase 7: HTTP integration where supported and complete backend gap handover.
22. Validate with install, typecheck and production build; user performs visual review.
23. Each phase stops for review. No Git staging, commits, branch changes, pushes or PR actions.
