# Bindr documentation

Use the current guides below. Dated handovers, source QA reports and archived provider notes remain in place to preserve their evidence and links; their passing verdicts apply only to the revision/scenario they recorded.

## Current project and implementation state

- [Project overview and branch/deployment boundaries](../README.md)
- [Repository audit](REPOSITORY_AUDIT_2026-11-15.md)
- [Combined integration evidence and remaining work](intelligence/COMBINED_MVP_STATUS.md)
- [Track A implementation status](IMPLEMENTATION_STATUS_A.md) and [Track B implementation status](IMPLEMENTATION_STATUS_B.md)
- [Original UI restoration](intelligence/ORIGINAL_UI_RESTORATION.md), [frontend incident](intelligence/FRONTEND_INCIDENT_2026-11-15.md) and [requested UI refinements](intelligence/UI_POLISH_2026-11-15.md)

## Run, configure and release

- [Frontend](../frontend/README.md) and [backend](../backend/README.md)
- [Environment configuration](ENVIRONMENT.md)
- [Authentication setup](AUTHENTICATION.md) and [account launch checklist](LOGIN_LAUNCH_CHECKLIST.md)
- [Cloud SQL, worker, retention and release operations](platform/OPERATIONS.md)
- [Existing Google Cloud v2 update and observed deployment](intelligence/CLOUD_V2_UPDATE.md)
- [Google Cloud resource/setup reference](DEPLOYMENT_GOOGLE_CLOUD.md)

The full existing-service updater is for schema/worker changes. The frontend hotfix updater reuses an existing backend image. The older deploy script alone does not prepare the v2 schema or scheduler. These are manual release paths, not an automatic consequence of a Git merge.

## Interfaces, plans and presentation

- [Published platform v2 packet](platform/API_V2_PACKET.md)
- [Track B profile and compatibility mapping](intelligence/INTERFACE_V2_B.md)
- [Frozen parallel implementation contract](PARALLEL_IMPLEMENTATION_CONTRACT.md)
- [Product roadmap](PRODUCT_IMPLEMENTATION_PLAN.md) and [two-person delivery plan](TWO_PERSON_DELIVERY_PLAN.md)
- [Editable 16:9 flowcharts and exports](diagrams/README.md)

## Historical evidence

[Original AI QA report](AI_QA_REPORT_SOURCE.md), [extreme-test report](EXTREME_TEST_REPORT.md), [earlier live acceptance](LIVE_ACCEPTANCE.md) and phase handovers are preserved. They do not establish that the new real v2 engine, original-screen integration, account/privacy checks, optional providers or current deployed revision have passed acceptance. Private conversation identifiers inside source reports are provenance references, not public repository links.
