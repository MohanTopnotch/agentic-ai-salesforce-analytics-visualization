# Phase 5 — System Deployment

**Status: Partial.** Docker and CI configuration exist. A local health check and
Compose configuration were verified; an actual release deployment is not
evidenced.

## Deployment package

- `deployment/Dockerfile`: builds the FastAPI container.
- `deployment/docker-compose.yml`: API plus Nginx frontend.
- `deployment/nginx.conf`: frontend serving/API proxy configuration.
- `frontend/`: static dashboard.
- `pyproject.toml`: package and runtime dependencies.
- `.env.example`: safe template for Salesforce environment configuration.

## Environment configuration

The app defaults to mock mode. For Salesforce live mode, set server-side
`SALESFORCE_MODE=live`, `SALESFORCE_CLIENT_ID`,
`SALESFORCE_CLIENT_SECRET`, and, when needed, `SALESFORCE_LOGIN_URL` and
`SALESFORCE_API_VERSION`. See [deployment README](../deployment/README.md).
Do not store credentials in Git, browser files, images, tickets, or this
handover. Supply production secrets using the deployment platform's secret
manager.

Live mode uses one Salesforce OAuth run-as identity. The application has no
individual user authentication; do not publicly expose the service until an
appropriate authentication and authorization layer is implemented.

## CI/CD pipeline

`.github/workflows/ci.yml` defines GitHub Actions CI for pushes and pull
requests to `main`/`master`, including Ruff, Bandit, Pytest, and test-result
artifact upload. The workflow configuration is present; a successful CI run or
automated deployment workflow is not evidenced here.

## Deployment and smoke test procedure

1. Configure a private environment and secrets.
2. Configure the approved Salesforce OAuth client and run-as user's read
   permissions.
3. Run `docker compose -f deployment/docker-compose.yml up --build`.
4. Check `http://localhost:8000/health` and `http://localhost:8000/docs`.
5. Open `http://localhost:8080`, submit the Lead revenue demo question, inspect
   the verification and lineage, and verify the result agrees with the sandbox.
6. Inspect service logs for sanitized failures; never print tokens or secrets.
7. Stop local containers with `docker compose -f deployment/docker-compose.yml down`.

Verified during this handover: Compose config validation and local API health
endpoint returned HTTP 200. **Not verified:** Docker image build/run, frontend
container, remote environment, or Salesforce live query.

## Release notes / known constraints

- Live mode is opt-in; default mode remains mock.
- Current SOQL is fixed and limited to 10 Leads; live client caps collected
  rows at 2,000.
- Output is Lead Annual Revenue by Industry, not closed-won sales.
- No production deployment target, release version/tag, rollback procedure,
  availability monitoring, or completed release note is evidenced.
- Do not advertise general natural-language analytics until dynamic planning,
  authorization, and business-approved test scenarios are complete.
