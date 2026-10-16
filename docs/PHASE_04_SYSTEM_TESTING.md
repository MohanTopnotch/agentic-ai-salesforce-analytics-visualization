# Phase 4 — System Testing

**Status: Partial.** Automated tests are available and were run locally for this
handover. Real-org, performance, and production security tests have not been
demonstrated.

## Test plan

| Test level | Purpose | Evidence / status |
|---|---|---|
| Unit | Validate calculations, query guard, client, agents, and orchestration | Present and passing |
| Salesforce adapter | Validate OAuth request handling, metadata/query shape, paging, mode config | Present with mocked HTTP responses; no real Salesforce credentials/API used |
| Integration | Submit API questions and check successful/invalid request handling | Present and passing against local app/mock workflow |
| Functional UI/E2E | Exercise browser through query, chart, table, and export | Not evidenced as an automated browser test |
| Performance/load | Validate throughput, latency, concurrent users, record limits | Not evidenced |
| Security | Validate auth, tenant/user isolation, secret handling, dependency and runtime behavior | SOQL guard and Bandit CI step exist; no completed security report or auth test |
| Live Salesforce | Validate OAuth, permissions, data shape, API limits, and business totals | Not run; requires configured org |

## Representative test cases

| ID | Scenario | Expected result |
|---|---|---|
| TC-01 | Valid analytics request in mock mode | Completed response with a verified result |
| TC-02 | Empty or missing question | HTTP 422 validation response |
| TC-03 | Disallowed SOQL object/field or mutation | Query rejected before execution |
| TC-04 | Calculation fixture with grouped revenue | Grouped totals reconcile |
| TC-05 | Mocked OAuth and query pagination | Access token applied; pages normalized and combined |
| TC-06 | Query continuation points to external URL | Client rejects the continuation URL |
| TC-07 | Live mode without client ID/secret | Configuration fails explicitly; no mock fallback |
| TC-08 | Salesforce API permission/provider error | Structured workflow failure; no fabricated successful result |
| TC-09 | Live org lacks required Lead field permission | Workflow fails; confirm with a Salesforce integration test before release |
| TC-10 | Query exceeds configured client-side record limit | Client returns a bounded query failure |

## Functional and integration test results

Latest recorded local verification:

- `python -m pytest`: **65 passed**.
- Ruff lint and format checks on changed Python files: passed.
- FastAPI startup and `GET /health`: HTTP 200, `{"status": "healthy"}`.
- Docker Compose configuration validation: passed.
- `git diff --check`: passed.

Tests use the local mock application and mocked HTTP behavior. No live Salesforce
account was contacted.

## Defects and limitations

No formal defect register or defect-resolution report is present. Known release
limitations:

- Default planner always queries Lead Annual Revenue by Industry, regardless
  of the user's requested metric/dimension.
- `Lead.AnnualRevenue` is not Closed Won Opportunity revenue.
- Application authentication, authorization, and multi-user isolation are not
  implemented.
- The in-memory session store is not durable.
- Browser-driven end-to-end, load, and live-org tests remain to be run.

## Test summary and exit criteria

The current code passes its automated local test suite. This supports a
mock-backed development demo, not a production-readiness claim. Before release,
complete and retain results for:

1. Business acceptance tests against agreed Salesforce fields and metrics.
2. Salesforce sandbox OAuth, permission-denial, pagination, API-limit, and
   representative record tests.
3. Browser E2E and accessibility checks.
4. Performance and security validation appropriate to the deployment.
5. Triage and closure of all release-blocking defects.
