# Agentic AI Salesforce Data Analytics & Visualization Assistant

Starter skeleton for a multi-agent application that answers natural-language questions about Salesforce data using metadata discovery, guarded read-only SOQL, deterministic analysis, visualization, grounded insights, conversation state, and audit/lineage.

**Status:** foundational skeleton only. Salesforce OAuth/API, production SOQL parsing, MCP server/client, LLM provider, frontend, persistence, and cloud deployment still need implementation.

## Run locally
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --reload
```
Open `http://127.0.0.1:8000/docs`.

The analytics endpoint intentionally returns `not_implemented` until the workflow is wired. It does not fabricate Salesforce results.

## Workflow
User Query → Query Understanding → Metadata Discovery → Query Plan → Safe SOQL → Data Retrieval → Deterministic Analysis & Verification → Visualization → Grounded Insights → Audit/Lineage.

## Technology baseline
Python 3.11+, FastAPI, Pydantic, pandas, Plotly-compatible JSON specs, pytest, Docker, GitHub Actions. Azure or AWS remains an implementation decision.

## Security principles
- Analytics is read-only; no Salesforce create/update/delete/upsert.
- Enforce object permissions and field-level security.
- Never execute raw model-generated SOQL without parser-based validation.
- Use deterministic code for financial calculations and reconciliation.
- Keep secrets out of source control and redact sensitive data from logs.

See `docs/` for requirements, design, API contracts, implementation plan, and test strategy.
