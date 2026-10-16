# Phase 3 — System Development

**Status: Partial.** This phase records source artifacts and what the code
actually implements; it is not a claim that every planned product feature is
complete.

## Source code and repository

The source is in this Git repository. Key areas:

- `app/api/`: FastAPI routes and request/response schemas.
- `app/orchestration/`: workflow state and orchestration.
- `app/salesforce/`: adapter contract, mock, factory, and live REST client.
- `app/security/`: SOQL guard.
- `app/analysis/`: calculations and reconciliation.
- `app/agents/`: reusable agent implementations.
- `app/mcp/`: optional MCP tools/server.
- `frontend/`: static browser dashboard.
- `tests/`: unit and API integration tests.

## Implemented features

1. Request validation, health endpoint, and structured workflow response.
2. Workflow request ID and explicit state progression.
3. Mock Salesforce data mode.
4. Optional live Salesforce REST/OAuth client with metadata discovery,
   pagination, timeout handling, and a bounded record count.
5. SOQL syntax, mutation, object, and field allowlist checks.
6. Deterministic Decimal grouping and reconciliation.
7. Visualization/insight response and frontend rendering/export.
8. Automated unit and HTTP integration coverage.

## API and service integrations

| Interface | Contract | State |
|---|---|---|
| `GET /health` | Health status | Implemented |
| `POST /api/v1/query` | Natural-language request and structured analytics result | Implemented; fixed query plan |
| Salesforce REST API | OAuth client credentials, describe, query | Implemented; requires org setup and has not been proven against a live org |
| MCP tools | Salesforce metadata/query tool surface | Present separately; not wired into the default API workflow |

## Database implementation

No database is configured. Mock Salesforce records are in-memory; workflow
sessions are also in-memory. No database migrations, persistent session store,
or database integration are evidenced.

## Tests and code review

Automated tests are present under `tests/`; the latest recorded local run for
this handover passed 65 tests. See [Phase 4 — System Testing](./PHASE_04_SYSTEM_TESTING.md)
for coverage scope and limitations.

No separate code-review report, approval, or formal review sign-off is present
in the repository. A passing linter or test suite is not a substitute for code
review.

## Development gaps

- General natural-language questions do not produce dynamic Salesforce queries.
- The default report is Lead Annual Revenue by Industry, not actual
  Opportunity Closed Won sales.
- No authenticated application-user identity or row-level user mapping exists.
- Audit logging is not configured by the default API dependency.
- Persistence, production observability, and deployment runtime configuration
  remain release work.
