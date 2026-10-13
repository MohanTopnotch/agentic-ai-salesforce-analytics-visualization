# Phase 8: Web UI & Deployment

## Included
- `frontend/`: responsive dashboard, natural-language query input, sample query chips, Plotly chart viewer, results table, CSV export, and verification/lineage panel.
- `deployment/Dockerfile`: builds the FastAPI service from the repository root.
- `deployment/docker-compose.yml`: starts the API and Nginx-served frontend.
- `deployment/nginx.conf`: serves the frontend and proxies `/api/` calls to FastAPI.

## Run from the repository root
Prerequisites: Docker Desktop running, and the project root contains a valid `pyproject.toml` that installs the package and includes FastAPI/Uvicorn dependencies.

```powershell
docker compose -f deployment/docker-compose.yml up --build
```

Open:
- Frontend: http://localhost:8080
- API: http://localhost:8000
- API docs: http://localhost:8000/docs

Stop:
```powershell
docker compose -f deployment/docker-compose.yml down
```

## API contract
The UI posts `POST /api/v1/query` with:
```json
{"question":"Show total sales by region.","user_id":"web-dashboard-user"}
```

It expects a response containing `request_id`, `status`, `state`, `data`, and `verified`. The chart renderer supports either a Plotly figure (`data` and `layout`) nested in `data.chart` / `data.visualization`, or a simple chart spec (`type`, `x`, `y`, `labels`, `values`, `title`). The table renderer looks for arrays in `data.rows`, `data.records`, `data.table.rows`, `data.results`, or `data.data`.

Adjust `frontend/app.js` to match the actual `AgentResult` / `OrchestrationResponse` response schema used by your project. The dashboard intentionally displays an error when the API returns `status: "error"`; it does not invent analytics results.

## Important compatibility checks
1. Ensure `pyproject.toml` declares `fastapi` and `uvicorn[standard]` as runtime dependencies.
2. Ensure `app.main:app` is the actual FastAPI import path.
3. The API health check expects `GET /health`. If your app only exposes `/api/v1/health`, update the Docker healthcheck URL accordingly.
4. The Dockerfile uses Python 3.12. If the code relies on Python 3.13+ features, select a compatible base image.
5. `SALESFORCE_MODE=mock` is used for local development. Do not place production secrets in this compose file; use a secret manager or deployment environment configuration.
