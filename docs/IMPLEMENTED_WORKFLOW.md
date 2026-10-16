# Implemented Workflow and Salesforce Data Source

## Current status

The API supports two data modes. It defaults to **mock data** for local
development. Set `SALESFORCE_MODE=live` and configure the backend OAuth client
credentials to retrieve data from one Salesforce org. Live mode uses the
Salesforce user configured as the OAuth application's run-as identity.

## What runs today

```text
Browser (frontend/app.js)
  -> POST /api/v1/query
  -> FastAPI route (app/api/routes.py)
  -> cached AnalyticsOrchestrator + configured Salesforce client
  -> MockSalesforceClient (mock mode) OR SalesforceRESTClient (live mode)
  -> query results -> deterministic analysis -> reconciliation
  -> visualization and insight response
  -> browser renders the response
```

The frontend submits the question without claiming a user identity. The API
still accepts an optional `user_id` from other callers, but it is not
authenticated or verified. In live mode, data access is determined by the one
configured Salesforce run-as user.

## Implemented request stages

The default workflow in `app/orchestration/orchestrator.py` does the following:

1. Creates a request context and request ID. It can retain follow-up history in
   an in-memory session store, scoped by the supplied `user_id` and session ID.
2. Produces a basic sales-analysis intent. The default implementation is
   deterministic; it does not call an LLM.
3. Discovers accessible objects and the `Lead` field metadata from the selected
   client. In live mode, Salesforce permissions for the OAuth run-as user apply.
4. Plans a fixed query:
   `SELECT AnnualRevenue, Industry FROM Lead LIMIT 10`. The plan is not
   generated dynamically from the question and only requests the fields needed
   for the current calculation.
5. Validates the query with `SOQLSafetyGuard` against the discovered objects
   and fields, then executes it through the selected client. Live queries use
   Salesforce REST API pagination and have a 2,000-record client-side cap.
   Query repair is bounded to three attempts, but the default repair handler
   reuses the fixed query plan.
6. Groups returned `AnnualRevenue` values by `Industry` and checks that group
   totals reconcile with the total of the raw records.
7. Stops with a failed workflow if verification does not pass; otherwise it
   creates a chart specification and deterministic insight text.
8. Returns the structured result through FastAPI to the browser.

**Metric caveat:** `Lead.AnnualRevenue` is the annual revenue value on Lead
records. It is not closed-won Opportunity revenue. The chart and insight label
this as Lead Annual Revenue; use an Opportunity-based plan (for example
`Opportunity.Amount` with an appropriate stage/date filter) for actual sales.

The frontend submits to the FastAPI service; it does not contact Salesforce
directly. The orchestration response includes query results, calculated data,
verification, visualization, insights, and lineage fields when the workflow
succeeds.

## Where data comes from

`get_orchestrator()` in `app/api/routes.py` calls
`create_salesforce_client()` in `app/salesforce/factory.py`. With the default
`SALESFORCE_MODE=mock`, it selects
`app.mock_salesforce_client.MockSalesforceClient()`, which contains sample
`Lead` records in Python memory. It does not read Salesforce or load the JSON
files under `data/mock_salesforce/`.

With `SALESFORCE_MODE=live`, the factory selects
`app.salesforce.rest_client.SalesforceRESTClient`. It requests an OAuth token
using the client-credentials flow and sends read-only REST API calls to the
instance URL returned by Salesforce.

## Implementation status by area

| Area | Current state |
| --- | --- |
| Browser-to-FastAPI request | Implemented |
| Orchestrated query/analysis/verification flow | Implemented with deterministic default handlers |
| Salesforce schema and records | Mocked by default; live REST client available through `SALESFORCE_MODE=live` |
| Dynamic intent-to-SOQL planning | Not implemented in the default workflow |
| Live Salesforce OAuth and API client | Implemented; requires Connected App configuration and backend secrets |
| `SOQLSafetyGuard` in the default query path | Wired for object and field allowlist validation |
| Application-user authentication/authorization | Not implemented; optional `user_id` is not authenticated |
| Audit logger | Available as a component, but not configured by the default API route |
| MCP server/tools | Present separately; not used by the default API route |
| Persistent conversation storage | Not implemented; sessions are in memory |

## How to select a Salesforce org

1. Register/configure an OAuth client-credentials flow in Salesforce and
   select the Salesforce user whose permissions should govern queries.
2. Set `SALESFORCE_MODE=live`, `SALESFORCE_CLIENT_ID`, and
   `SALESFORCE_CLIENT_SECRET` on the backend. Set `SALESFORCE_LOGIN_URL` for
   production or sandbox as appropriate; the API version is configurable.
3. Start/restart the API. Startup validates the configuration; the orchestrator
   receives the configured adapter through `get_orchestrator()` in
   `app/api/routes.py` and uses it for metadata discovery and query execution.
4. Verify that the connected Salesforce user can query `Lead` and read
   `AnnualRevenue` and `Industry`. A missing object/field permission or rejected
   OAuth configuration is reported as a workflow error, not replaced with mock
   data.
5. Keep the service private until application-user authentication is added. The
   current UI's `user_id` field is caller supplied and is not a login.
6. For questions other than the fixed Lead revenue analysis, implement a
   dynamic, metadata-aware planner and update the analysis fields; the current
   query does not answer arbitrary prompts despite accepting them.

The Salesforce user/setup screen alone is not enough to connect the application:
the backend still needs the OAuth application configured and its client
credentials set. Do not send a Salesforce password, security token, or client
secret in chat.

## Code map

- API request/response contract: `app/api/schemas.py`
- API route and orchestrator dependency: `app/api/routes.py`
- Client mode selection: `app/salesforce/factory.py`
- Workflow stages and default client construction:
  `app/orchestration/orchestrator.py`
- Salesforce client interface: `app/salesforce/client.py`
- Live Salesforce REST/OAuth client: `app/salesforce/rest_client.py`
- In-memory mock used by the default workflow: `app/mock_salesforce_client.py`
- Other mock client: `app/salesforce/mock_client.py`
- SOQL validation implementation: `app/security/soql_guard.py`
- Deterministic calculation and reconciliation:
  `app/analysis/calculation.py`, `app/analysis/verification.py`
- Browser request and rendering: `frontend/app.js`
- Local container configuration: `deployment/docker-compose.yml`
