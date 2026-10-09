# Initial API Contracts

## GET /health
Returns service status.

## GET /api/v1/health
Returns API status.

## POST /api/v1/analytics/query
Request:
```json
{
  "question": "Show sales pipeline by region for the current quarter",
  "session_id": "optional-session-id",
  "user_id": "optional-authenticated-user-id",
  "role": "optional-role",
  "conversation_history": []
}
```

Current skeleton returns `status: not_implemented`, empty data, `verification.status: not_run`, lineage unavailable, and a request/audit ID. A future successful response should include verified data, intent/plan summary, chart specification, grounded insights, verification, lineage, and audit ID. Never return credentials or unauthorized records.
