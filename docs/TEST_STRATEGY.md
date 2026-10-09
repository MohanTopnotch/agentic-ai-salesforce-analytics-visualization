# Test Strategy

## Unit tests
Intent parsing; query plan and follow-up deltas; SOQL validation; calculations; nulls/rounding/currency/time zones; reconciliation; chart spec; PII masking; audit redaction.

## Integration tests
Salesforce sandbox auth/metadata/query; least-privilege access; MCP schemas; session/audit/lineage persistence; LLM timeout/rate-limit behavior.

## End-to-end benchmark
Cover sales, opportunities, customers, leads, performance, and follow-ups. Each case should define expected objects/fields, filters, formulas, expected values from controlled fixtures, chart intent, and evidence for insights.

## Security tests
Reject mutations and arbitrary tool calls; enforce object/field access; test prompt injection from user and CRM data; verify no secret/PII leakage; confirm query repair never removes security constraints.

## Quality gates
Set coverage baseline and target (proposed initial target: 80% line coverage, with critical security paths fully tested). Track correctness, groundedness, query validity, clarification behavior, latency, and cost.
