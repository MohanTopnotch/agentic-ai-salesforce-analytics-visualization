# Phase 8: Web UI & Deployment

## Included
- `frontend/`: responsive dashboard, natural-language query input, sample query chips, Plotly chart viewer, results table, CSV export, and verification/lineage panel.
- `deployment/Dockerfile`: builds the FastAPI service from the repository root.
- `deployment/docker-compose.yml`: starts the API and Nginx-served frontend.
- `deployment/nginx.conf`: serves the frontend and proxies `/api/` calls to FastAPI.

## Run from the repository root

Prerequisite: Docker Desktop is installed and running. A host Python installation
or `.venv` is **not** required to build or run the containers. The API image uses
Python 3.12 and installs the project dependencies from `pyproject.toml` inside
the image. `.dockerignore` excludes any local `.venv` from the Docker build
context.

```powershell
docker compose -f .\deployment\docker-compose.yml config
docker compose -f .\deployment\docker-compose.yml up --build
```

Open:
- Frontend: http://localhost:8080
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

Stop:
```powershell
docker compose -f .\deployment\docker-compose.yml down
```

`python -m pip install ruff` and activating `.venv` are only relevant to local
Python development and linting; they are not prerequisites for Docker Compose.
For local development on Windows, create and activate an environment separately:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
```

## Salesforce data source

The API defaults to `SALESFORCE_MODE=mock`. To use a Salesforce org, configure
an OAuth client-credentials flow for a Salesforce Connected App (or External
Client App) and set its run-as identity to the Salesforce user whose data the
application should read. Grant that user API access and the required Lead
object/field permissions.

In Salesforce Setup, create the OAuth application, enable the client-credentials
flow, assign its run-as user, and grant that user API Enabled plus read access
to the Lead object and the `AnnualRevenue` and `Industry` fields.

For local development, copy `.env.example` to `.env` in the repository root,
then set:

```dotenv
SALESFORCE_MODE=live
SALESFORCE_LOGIN_URL=https://login.salesforce.com
SALESFORCE_API_VERSION=v66.0
SALESFORCE_CLIENT_ID=your-connected-app-client-id
SALESFORCE_CLIENT_SECRET=your-connected-app-client-secret
```

Use `https://test.salesforce.com` for a sandbox. Keep `.env` untracked and never
put these values in frontend files or source control. In deployed environments,
inject them from the platform's secret manager. Live mode fails at API startup
if the client ID or secret is missing; it does not fall back to mock records.
Configuration is checked as the API starts.

The default planner supports a documented set of Lead and Opportunity analytics
and asks for clarification for unsupported requests; it does not translate
arbitrary natural language into SOQL. A single Salesforce run-as user supplies
the permissions for every request; the current web UI's `user_id` is not
authentication. Do not expose this service publicly until application-user
authentication and authorization are added.

## API contract
The UI posts `POST /api/v1/query` with:
```json
{"question":"Show lead annual revenue by industry."}
```

It expects a response containing `request_id`, `status`, `state`, `data`, and `verified`. The current chart is in `data.visualization`; raw query results are in `data.query_results`, and aggregated rows are in `data.calculated_data`.

The dashboard intentionally displays an error when the API returns `status: "error"`; it does not invent analytics results. The fixed query is Lead Annual Revenue by Industry, not arbitrary sales analysis or Closed Won Opportunity revenue.

## Important compatibility checks
1. Ensure `pyproject.toml` declares `fastapi` and `uvicorn[standard]` as runtime dependencies.
2. Ensure `app.main:app` is the actual FastAPI import path.
3. The API health check expects `GET /health`. If your app only exposes `/api/v1/health`, update the Docker healthcheck URL accordingly.
4. The Dockerfile uses Python 3.12. If the code relies on Python 3.13+ features, select a compatible base image.
5. Salesforce mode defaults to `mock`. See the Salesforce data-source section
   to enable `live`; do not put production secrets in this compose file, and use
   a secret manager or deployment environment configuration.
