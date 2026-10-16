# Phase 6 — Final Product Demo and Handover

**Status: Partial.** A mock-backed end-to-end demonstration is available. A
live-org presentation and final stakeholder sign-off remain pending.

## Working application

The repository contains a FastAPI service and static dashboard. Run from the
repository root in PowerShell:

```powershell
docker compose -f deployment/docker-compose.yml up --build
```

Open:

- Dashboard: `http://localhost:8080`
- API docs: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`

For a local run without Docker, use the project environment and start
`uvicorn app.main:app --reload`. The default source is mock data.

## End-to-end demonstration

1. Open the dashboard and submit a question such as “Show total sales by
   region.”
2. Explain that the current implementation uses a fixed Lead query, not a
   dynamic interpretation of that exact requested metric.
3. Show the resulting Lead Annual Revenue by Industry chart/table, verification
   status, request ID, and lineage.
4. Show API schema/docs and health endpoint.
5. Explain how `SALESFORCE_MODE=live` selects the Salesforce adapter, without
   displaying or sharing secret values.
6. State explicitly that no live-org query is part of the verified demo unless
   a sandbox has been separately configured and tested.

The Docker demonstration procedure is in
[deployment/README.md](../deployment/README.md).

## Demo scenarios

| Scenario | Demo action | Expected outcome | Mode |
|---|---|---|---|
| D-01: Successful analysis | Submit a sample question | Verified grouped Lead revenue, visualization, and lineage | Mock |
| D-02: Input validation | Submit blank question using API docs | HTTP 422; no query result | Mock |
| D-03: Unsupported query/field | Run unit test or controlled guard test | Rejected before provider execution | Test fixture |
| D-04: Salesforce OAuth configuration missing | Set live mode without credentials and start app | Startup fails clearly; no mock fallback | Local configuration test |
| D-05: Live Salesforce query | Configure sandbox, test OAuth identity and permissions, submit request | Live Lead records or explicit authorization/provider error | Sandbox only; not yet verified |

## Product presentation outline

1. Problem: sales data questions require manual reports and queries.
2. Proposed experience: natural-language question to verified visualization.
3. Demonstrate the current working Lead revenue workflow and validation.
4. Explain the Salesforce adapter modes and responsible secret handling.
5. Be transparent about current boundaries: fixed plan, Lead metric, no
   per-user authentication, and no arbitrary question support.
6. Present next steps: agree business metrics, add dynamic planning, add
   authentication, run sandbox acceptance tests, then deploy privately.

## Technical documentation included

- [Project deliverables index](./PROJECT_DELIVERABLES.md)
- [Requirements analysis](./REQUIREMENTS.md)
- [Phase 1 analysis](./PHASE_01_REQUIREMENT_ANALYSIS.md)
- [System design](./SYSTEM_DESIGN.md)
- [Implemented workflow and Salesforce data source](./IMPLEMENTED_WORKFLOW.md)
- [Phase 2 design assessment](./PHASE_02_SYSTEM_DESIGN.md)
- [Phase 3 development assessment](./PHASE_03_SYSTEM_DEVELOPMENT.md)
- [Phase 4 testing report](./PHASE_04_SYSTEM_TESTING.md)
- [Phase 5 deployment report](./PHASE_05_SYSTEM_DEPLOYMENT.md)
- [Deployment instructions](../deployment/README.md)

## Final handover checklist

- [x] Source code and local Git repository.
- [x] Mock-mode application and test suite.
- [x] Salesforce adapter interface and opt-in OAuth REST client.
- [x] Environment template without credentials.
- [x] Requirements, design, workflow, testing, deployment, and phase-status docs.
- [x] Local automated test and health-check evidence recorded.
- [ ] Salesforce Connected App configured by org administrator.
- [ ] Live sandbox query and permission test accepted.
- [ ] Business KPIs and Salesforce field mapping approved.
- [ ] Application authentication/authorization implemented before public access.
- [ ] Production environment, secrets, monitoring, backup, and rollback configured.
- [ ] Product owner acceptance and release sign-off recorded.

## Handover safety

Never include Salesforce client secrets, access tokens, passwords, or security
tokens in the presentation or handover. Transfer credentials only through the
approved secret manager and grant the integration identity only the minimum
read permissions required.
