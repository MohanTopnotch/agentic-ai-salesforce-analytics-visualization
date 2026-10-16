# Project Deliverables and Handover Index

This index maps the requested project lifecycle deliverables to separate
phase documents and the evidence present in this repository. Status describes
the current checked-in project, not a proposed future state.

## Status key

- **Implemented**: present in code or documentation and verified where noted.
- **Partial**: a working subset exists; scope or evidence is incomplete.
- **Not evidenced**: no implementation or artifact in this repository confirms
  completion. This does not assert that no work was done outside the repository.

## Lifecycle deliverables

| # | Phase | Status | Main evidence / outstanding items |
|---|---|---|---|
| 1 | Requirement Analysis | Partial | [Requirements analysis](./REQUIREMENTS.md) captures scope and acceptance criteria. Business definitions, Salesforce org schema, stakeholder-approved use cases, and final acceptance sign-off remain open. |
| 2 | System Design | Partial | [System design](./SYSTEM_DESIGN.md) describes the target architecture; [Phase 2 analysis](./PHASE_02_SYSTEM_DESIGN.md) identifies the design vs. implemented gaps. Detailed database design is not applicable to current in-memory session storage; persistence design is pending. |
| 3 | System Development | Partial | Application, API, UI, mock and live Salesforce REST adapter, SOQL guard, calculations, and tests are in the repository. Dynamic natural-language query planning, user authentication, persistent database, and formal code-review sign-off are not evidenced. |
| 4 | System Testing | Partial | Automated tests and test evidence are summarized in [Phase 4](./PHASE_04_SYSTEM_TESTING.md). Functional and mocked-adapter tests pass; real Salesforce, load/performance, and security validation have not been demonstrated. |
| 5 | System Deployment | Partial | Docker assets and CI workflow exist. Compose configuration and local health endpoint have been checked; no deployed environment, CI run, production secrets configuration, or live Salesforce smoke test is evidenced. |
| 6 | Final Product Demo | Partial | A mock-backed demo can be run locally using [Phase 6 scenarios and handover](./PHASE_06_FINAL_HANDOVER.md). A live-account demo and final business-owner acceptance are pending. |

## Phase documents

1. [Requirement Analysis](./PHASE_01_REQUIREMENT_ANALYSIS.md)
2. [System Design](./PHASE_02_SYSTEM_DESIGN.md)
3. [System Development](./PHASE_03_SYSTEM_DEVELOPMENT.md)
4. [System Testing](./PHASE_04_SYSTEM_TESTING.md)
5. [System Deployment](./PHASE_05_SYSTEM_DEPLOYMENT.md)
6. [Final Product Demo and Handover](./PHASE_06_FINAL_HANDOVER.md)

## Existing technical references

- [Requirements Analysis](./REQUIREMENTS.md)
- [System Design](./SYSTEM_DESIGN.md)
- [Implemented Workflow and Salesforce Data Source](./IMPLEMENTED_WORKFLOW.md)
- [Deployment Instructions](../deployment/README.md)
- [CI workflow](../.github/workflows/ci.yml)
- [Application source](../app/)
- [Frontend](../frontend/)
- [Automated tests](../tests/)
- [Deployment package](../deployment/)

## Final handover caveats

- The default app mode is mock. Live mode requires a Salesforce OAuth
  client-credentials app and backend secrets.
- The live adapter uses the configured Salesforce run-as user. The web
  application does not authenticate individual users.
- The default query is fixed to `Lead.AnnualRevenue` and `Industry`; it is not a
  general natural-language-to-SOQL product and Lead annual revenue is not
  closed-won Opportunity sales.
- There is no production database, production deployment, live Salesforce
  account validation, performance report, or formal security sign-off in this
  repository.
- Do not provide Salesforce credentials as part of the handover document or
  commit them to source control.
