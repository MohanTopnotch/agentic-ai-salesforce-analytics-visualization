# Phase 1 — Requirement Analysis

**Status: Partial.** The project-level requirement baseline is in
[REQUIREMENTS.md](./REQUIREMENTS.md). This document maps the requested
requirement-analysis deliverables to the evidence and open decisions.

## Problem statement

Sales and operations users need to ask questions of Salesforce data without
manually composing SOQL or spreadsheets. The intended product translates a
question into a safe query, retrieves authorized records, calculates and
verifies measures, then presents results in a chart/table with traceable
context.

The current implementation demonstrates that flow with a constrained fixed
Lead query. It does not yet satisfy arbitrary business questions.

## Requirements and status

| Requirement area | Current project evidence | Status / remaining work |
|---|---|---|
| Natural-language questions | `POST /api/v1/query` accepts a question; default intent handler is deterministic | Partial: questions do not dynamically change the query |
| Salesforce data | Mock data by default; optional live REST adapter | Partial: live OAuth must be configured and validated against the target org |
| Safe access | Read-only query guard checks query grammar and discovered object/field allowlists | Partial: server-side application-user authentication is absent; adapter tests are simulated |
| Analysis | Deterministic decimal aggregation by Lead Industry and reconciliation | Implemented for the fixed measure/dimension |
| Visualization and insight | Response includes visualization and deterministic insight data | Partial: output is fixed to Lead Annual Revenue by Industry |
| Follow-up questions | In-memory conversation/session support exists | Partial: persistence and complete dynamic query-state handling are absent |
| Audit and lineage | Request ID and query lineage are returned; audit logger component exists | Partial: audit logger is not configured by default API route |
| Reliability | Workflow returns structured status and errors; bounded query repair | Partial: production retry/monitoring behavior has not been validated |

## Functional requirements

The principal functional requirements and IDs are documented in
[REQUIREMENTS.md](./REQUIREMENTS.md), including query understanding, schema
discovery, safe SOQL, calculation, visualization, follow-up, auditing, errors,
insights, and Salesforce integration.

Implementation scope at handover:

1. Accept and validate an analytics question.
2. Discover the Lead object's metadata from the selected Salesforce client.
3. Validate and execute `SELECT AnnualRevenue, Industry FROM Lead LIMIT 10`.
4. Aggregate Lead annual revenue by industry and reconcile totals.
5. Return chart, insights, verification status, and query lineage.

## Non-functional requirements

Security, reliability, testability, maintainability, performance, observability,
and reproducibility are listed in [REQUIREMENTS.md](./REQUIREMENTS.md).
Current evidence supports modular code, a SOQL allowlist guard, deterministic
calculation, tests, and a record cap in the live client. It does **not** establish
production security, load capacity, deployment availability, or operational
observability.

## Use cases

| Use case | Expected user outcome | Current support |
|---|---|---|
| View Lead Annual Revenue by Industry | Display grouped values and a chart with verification | Supported through the fixed query |
| Ask a different sales question | Resolve requested Salesforce objects, filters, and metrics | Not supported by the default planner |
| Connect a Salesforce org | Retrieve data through a configured OAuth identity | Adapter implemented; org setup and live validation remain |
| Refine a previous request | Reuse prior intent and conversation context | Partial; in-memory only and query plan remains fixed |
| Export results | Download rendered tabular results | UI has CSV export; verify end-to-end with target response shape before release |

## Acceptance criteria

Existing baseline acceptance criteria are recorded in section 10 of
[REQUIREMENTS.md](./REQUIREMENTS.md). For an honest release gate, also require:

- Confirm approved Salesforce OAuth flow and run-as user with the org owner.
- Verify the run-as user can read `Lead.AnnualRevenue` and `Lead.Industry`.
- Agree whether the requested sales KPI is Lead Annual Revenue or
  Opportunity-based sales; do not label the former as closed-won revenue.
- Demonstrate that object/field access denial and Salesforce API errors do not
  return mock data as a success.
- Obtain business-user acceptance for the actual demo scenarios and outputs.

## Open decisions

- Exact Salesforce objects, custom fields, stages, currencies, and reporting
  definitions.
- Whether users need individual Salesforce authorization or one private
  service-user connection.
- Whether to add a persistent database and audit retention policy.
- Which natural-language/LLM provider, if any, should be used.
- Target deployment platform, access model, availability, performance, and
  retention requirements.
