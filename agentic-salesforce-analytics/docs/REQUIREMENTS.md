# Requirement Analysis

## Objective
Enable business users to query Salesforce data in natural language. Discover objects/fields, retrieve data with safe read-only SOQL, analyze and verify metrics, visualize results, provide grounded insights, and support conversational follow-up.

## Functional requirements
1. Natural-language query and conversation.
2. Secure Salesforce connection.
3. Metadata discovery: objects, fields, types, relationships, permissions.
4. Validated read-only SOQL retrieval.
5. Deterministic analysis and independent verification.
6. Interactive charts and tables.
7. Evidence-backed summaries and insights.
8. Follow-up refinement of filters, periods, dimensions, metrics, and chart type.
9. Error handling, bounded repair, and clarification.
10. Authentication, role access, FLS, and PII handling.
11. Data lineage and explainability.
12. Audit trail and activity history.

## Non-functional requirements
Security, correctness, reliability, performance targets, maintainability, observability, scalability, usability, and cloud portability.

## Query categories
Sales by region; top representatives; monthly/yearly revenue; opportunity pipeline/stage; opportunities above $100K; top customers; customers without recent purchases; lead conversion by source; performance against targets; follow-ups such as top 5, compare with last year, and explain regional changes.

## Assumptions and constraints
Salesforce schemas vary by organization; permissions of the authenticated identity are authoritative. The system is analytics-only. Business definitions such as revenue, conversion, targets, current quarter, and close likelihood must be agreed. Credentials, LLM provider, MCP framework, frontend, persistent store, and cloud provider are deployment decisions. Mock mode is only for early development.

## Risks and mitigations
- Wrong fields/objects: discover live metadata and validate plans.
- Unsafe queries: parser, allowlists, FLS, read-only adapter.
- Hallucinated metrics: deterministic calculations and verification.
- Ambiguous definitions: ask clarification and document definitions.
- Data leakage: minimize fields, mask PII, redact logs.
- Provider outages: timeouts, structured errors, bounded retries.
- Follow-up drift: store structured session state and modify only requested attributes.
- Secret leakage: use environment secrets locally and cloud secret managers in deployment.

## Acceptance criteria
- Health API works.
- Intent/query plans are typed and inspectable.
- No query executes before syntax, read-only, object/field permission, timeout, and row-limit checks.
- Ambiguity produces clarification rather than invented results.
- Metrics include verification status and source provenance.
- Charts reflect verified data.
- Follow-ups preserve prior state unless the user changes it.
- Audit includes request IDs, objects/fields, status, result count, and verification without secrets.
- Unit/integration/security/end-to-end tests run in CI.
- Cloud setup, configuration, rollback, and demo are documented.
