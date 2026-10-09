# Implementation Plan

## Phase 0 — Foundation
- [ ] Create repository, branch policy, formatting/linting, and secret policy.
- [ ] Confirm business definitions and benchmark queries.
- [ ] Define sample Salesforce objects and fixtures.

## Phase 1 — API and mock mode
- [ ] Run FastAPI and validate request/response contracts.
- [ ] Implement deterministic mock Account, Opportunity, Lead, User, and quota fixtures.
- [ ] Implement mock metadata discovery and query execution.
- [ ] Add structured error and query-plan models.

## Phase 2 — Intent and discovery
- [ ] Implement schema-constrained intent extraction.
- [ ] Implement metadata search, relationships, and permissions.
- [ ] Add business-term catalog and ambiguity clarification.
- [ ] Generate structured query plans before SOQL.

## Phase 3 — Salesforce and safe SOQL
- [ ] Implement approved OAuth flow and token refresh.
- [ ] Implement describe/query adapter and integration tests against sandbox.
- [ ] Replace regex guard with parser/query builder.
- [ ] Enforce FLS, allowlists, row limit, timeout, and bounded repair.

## Phase 4 — Analysis and verification
- [ ] Implement aggregation, rankings, growth, conversion, and date comparisons.
- [ ] Define currency, null, duplicate, and time-zone behavior.
- [ ] Add independent reconciliation and provenance.

## Phase 5 — Visualization and insights
- [ ] Implement chart selection and validated Plotly specs.
- [ ] Generate insights only from verified metrics.
- [ ] Label uncertainty and distinguish correlation from causation.

## Phase 6 — Conversation, audit, lineage
- [ ] Persist structured follow-up state.
- [ ] Support top-N, date comparison, filter refinement, and diagnostic follow-ups.
- [ ] Persist audit/lineage and apply masking/retention controls.

## Phase 7 — UI, evaluation, deployment
- [ ] Build chat, charts, tables, summary, verification badge, and lineage view.
- [ ] Create benchmark set for all example categories.
- [ ] Add unit, integration, security, E2E, and load tests.
- [ ] Add CI security/dependency checks.
- [ ] Containerize, deploy to selected cloud, configure secrets/monitoring, document rollback, and prepare demo.

## Definition of done
Acceptance criteria documented; tests pass; security review completed for affected paths; no secrets in source/logs; provenance and docs updated; CI passes; changes reviewed.
