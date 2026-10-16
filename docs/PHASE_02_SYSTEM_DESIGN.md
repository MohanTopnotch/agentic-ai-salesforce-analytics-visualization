# Phase 2 — System Design

**Status: Partial.** [SYSTEM_DESIGN.md](./SYSTEM_DESIGN.md) records the target
architecture. The current runtime and its gaps are documented in
[IMPLEMENTED_WORKFLOW.md](./IMPLEMENTED_WORKFLOW.md).

## Technical and solution design

The solution is a Python FastAPI service with a browser dashboard. An API
request is sent to an orchestrator; the orchestrator calls the configured
Salesforce client, validates SOQL, calculates and reconciles a result, then
returns a response for rendering in the browser.

## System architecture

```text
Browser dashboard
    | POST /api/v1/query
    v
FastAPI request validation
    v
AnalyticsOrchestrator
    +--> intent (deterministic default)
    +--> Salesforce metadata (Lead)
    +--> fixed SOQL plan -> SOQLSafetyGuard
    +--> Salesforce client
    |       +--> in-memory mock (default)
    |       +--> REST API/OAuth (SALESFORCE_MODE=live)
    +--> deterministic analysis and reconciliation
    +--> visualization / insight / lineage response
    v
Browser results dashboard
```

The target design in `SYSTEM_DESIGN.md` includes specialized agents, MCP, and
authentication. Not all of those components participate in the current API
execution path.

## Component design

| Component | Responsibility | Current implementation |
|---|---|---|
| Frontend | Submit question; render status, chart, rows, export, lineage | Static HTML/CSS/JavaScript |
| FastAPI | Validate request, call orchestrator, serialize response | `/api/v1/query`, `/health` |
| Orchestrator | Coordinate request lifecycle and return structured status | Implemented; default handlers are fixed/deterministic |
| Salesforce client | Describe objects/fields and execute SOQL | Shared interface; mock and live REST implementations |
| SOQL guard | Reject unsafe syntax and fields/objects outside discovered allowlists | Used by default query-validation stage |
| Analysis | Group values and reconcile totals | Decimal-based Lead revenue by Industry |
| Audit | Record request execution | Logger exists; not configured in default API dependency |
| MCP | Expose Salesforce tools | Separate modules; not used by default HTTP workflow |

## Database and data design

There is no configured application database. Salesforce is the external source
of records; mock records are in Python memory. Conversation history is held in
the orchestrator's in-memory session dictionary and is lost at process restart.
No database schema, migrations, persistence, or backup/restore design is
implemented. A production persistence design must define session, audit, data
retention, access-control, and deletion requirements before choosing a store.

## Integration design

- API: browser calls `POST /api/v1/query`.
- Salesforce: `SalesforceClient` contract; `SALESFORCE_MODE` selects mock or
  OAuth client-credentials REST adapter.
- Credentials: backend environment/secret manager only.
- CI: GitHub Actions runs Ruff, Bandit, and Pytest on push/PR to `main` or
  `master`.
- MCP is an optional separate integration surface, not an active API dependency.

## Technology stack

| Layer | Technology |
|---|---|
| Language/runtime | Python 3.11+ project requirement; deployment image Python 3.12 |
| API | FastAPI, Pydantic, Uvicorn |
| Data calculations | Python `Decimal`, existing calculation helpers |
| Salesforce | Salesforce REST API; standard-library HTTP/OAuth implementation |
| UI | HTML, CSS, JavaScript, Plotly renderer |
| Packaging/deployment | `pyproject.toml`, Docker, Docker Compose, Nginx |
| Quality | Pytest, Ruff, GitHub Actions; Bandit configured in CI |

## UI/UX design

The dashboard includes natural-language input and example chips, a query
execution status, chart and result-table areas, CSV export, a verification
indicator, request ID, and lineage panel. The HTML/CSS/JS implementation is in
`frontend/`. No separate design-system specification, usability study, or
accessibility audit is evidenced.

## Design gaps before a production release

- Add application authentication and authorization before exposing the API.
- Use a metadata-aware planner that maps intent to approved org-specific fields.
- Decide on per-user Salesforce authorization vs. a restricted service identity.
- Define a real persistence, audit, retention, and observability design.
- Define production deployment, scaling, backup, and recovery requirements.
- Validate visualizations and response contract against business-approved
  scenarios.
