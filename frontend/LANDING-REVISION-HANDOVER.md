# Landing revision handover

Completed 14 Nov 2026. Revision to Phase 1; Phase 2 is not started.

## Follow-up visual cleanup

Applied Tushar's screenshot feedback: removed the hero helper sentence, Replay control, conversation caption, below-hero category strip, preview demo label/caption, synthetic-source note and photograph caption. Replaced NovaMart in landing artwork only with the real local Flipkart logo; the product preview uses a single “Refund example” breadcrumb for context. The brand affiliation note was explicitly retained. Mock adapter fixtures are unchanged. Product typography now uses Inter 16px body and 14px metadata, Nunito headings, and no monospace identifiers in the landing preview. Removed decimal styling from the amount. Production build, including TypeScript, passes after this cleanup. No dependencies were added in this follow-up. The sections below describe the initial revision and are superseded by this cleanup where noted.

## Result

The consumer SVG direction is implemented in the React landing page. Large Nunito headings replace small marketing typography; Inter remains for body/controls. White, indigo and lilac surfaces, borders and no shadows are preserved. The approved headline and main Track a promise action remain.

The technical infrastructure illustration is replaced by an original/revised message sequence with a Replay control and a link to the product example. The case preview has larger text and source controls. Workflow steps, an everyday photograph, a clearly labelled company-example strip, factual privacy section, FAQ and closing artwork complete the page.

Motion: one-time headline/message entrances, drawn heading underline, chronological message cards, replay, offscreen section reveals, scroll-position timeline fill, source-change highlight/transition, reading progress and arrow hover feedback. CSS and lightweight React effects are used, with no animation library. Listeners and observers are cleaned up. Reduced-motion renders static visible content; no continuous loops or scroll interception are used.

## Changes

- Modified: src/pages/Landing.tsx, src/components/ProductPreview.tsx, src/main.tsx, package.json, package-lock.json and .gitignore.
- Added: src/landing.css, src/components/PromiseConversation.tsx, src/components/LandingMotion.tsx, public/media/ assets, ASSETS.md and this handover.
- Dependency added: @fontsource/nunito. Existing fonts remain local.
- Local design-previews/ ignored; no research screenshots staged/copied into runtime assets.
- No contract, backend, API adapter or app route changes. No Git mutations or deployment.

## Validation

- `npm install @fontsource/nunito --no-audit --no-fund --fetch-retries=0 --fetch-timeout=20000`: passed with network-enabled execution.
- `npm run build`: passed (TypeScript + Vite).
- `npm run typecheck`: passed.
- Development server remains at http://127.0.0.1:5173/; HTTP 200 verified.
- Asset files inspected; PNG/JPEG/SVG originals are local. Photograph viewed during implementation.
- Browser visual pass unavailable: local browser access returned unavailable in this chat. No desktop/mobile screenshot or runtime interaction test is claimed. Tushar should review the live page at desktop and phone widths, source selection, replay, FAQ and footer dialogs.

## Remaining scope / limitations

The new page is ready for visual review. Dashboard/capture routes still show the Phase 1 checkpoints. Existing GAPS.md remains applicable: no backend is added by this design revision. Photography is illustrative stock, not a real customer. Brand examples do not imply integrations, affiliation or endorsements. Source/license details are in ASSETS.md.

The original reference board contains structural/partial matches; it does not establish an 80% match for every section or provide reference animation evidence. The playful SVG and Tushar's subsequent feedback supply the visual direction.

## Manual commit and push (Command Prompt)

After visual approval, run one command at a time. If any command errors, stop.

```cmd
cd /d "C:\Users\Test\OneDrive\Documents\ChatGPT\PromiseKeeper - VIHAANX\bindr-app"
git branch --show-current
git add frontend/
git --no-pager diff --cached --stat
git commit -m "feat(frontend): refresh Bindr landing visuals and motion"
git push origin feature/frontend
```

The branch should be feature/frontend. Staged paths should all start frontend/. docs/ remains unstaged; design-previews/, .env files, dist and node_modules are ignored. These commands are instructions only and were not executed by the assistant.

Stop for Tushar's review before Phase 2.
