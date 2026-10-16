# System Design — Agentic AI Salesforce Data Analytics & Visualization Assistant

> **Implementation status:** This document describes the target architecture.
> The API defaults to an in-memory mock client and deterministic default
> handlers. A client-credentials Salesforce REST client can be enabled with
> `SALESFORCE_MODE=live`; the default query planner remains fixed to Lead
> revenue analysis. Standalone MCP tools are not wired into the API workflow.
> See [IMPLEMENTED_WORKFLOW.md](./IMPLEMENTED_WORKFLOW.md) for details.

## 1. Architecture Overview

The target system accepts natural-language questions through a web interface or
API. A FastAPI service authenticates the request and passes it to an
orchestrator. In the current implementation, the API validates the request
schema but does not authenticate the caller.

The orchestrator coordinates specialized agents and shared services. The LLM is responsible for interpreting the user's intent and generating explanations. Deterministic application code is responsible for authorization enforcement, safe query construction, calculations, and verification.

## 2. High-Level Architecture

```text
User / Web UI
     |
     v
FastAPI API
     |
     v
Authentication and Authorization
     |
     v
Agent Orchestrator
     |
     +--> Query Understanding Agent
     |
     +--> Schema Discovery Agent
     |
     +--> Query Plan Builder
     |
     +--> SOQL Generation and Execution Agent
     |          |
     |          v
     |     SOQL Safety Guard
     |          |
     |          v
     |     MCP Tool Interface
     |          |
     |          v
     |     Salesforce API
     |
     +--> Data Analysis and Auditor Agent
     |          |
     |          v
     |     Deterministic Verification
     |
     +--> Visualization Agent
     |
     +--> Insight and Diagnostic Agent
                |
                v
       Response + Audit + Lineage
```

## 3. Component Responsibilities

### 3.1 FastAPI API

* Accept analytics requests.
* Validate request schemas.
* Enforce authentication and authorization.
* Return structured responses and errors.
* Provide health and readiness endpoints.

### 3.2 Query Understanding Agent

* Interpret the user's question.
* Identify the requested metric, dimensions, filters, date range, and ranking.
* Identify missing or ambiguous information.
* Produce a structured intent rather than executable SOQL.

### 3.3 Schema Discovery Agent

* Discover available Salesforce objects and fields.
* Inspect field types and supported relationships.
* Confirm that the requesting user may access the required data.
* Return validated metadata to the query planning stage.

### 3.4 Query Plan Builder

* Convert the interpreted intent into a structured query plan.
* Validate metrics, dimensions, filters, grouping, ordering, and limits.
* Map business terminology to approved Salesforce fields.
* Reject unsupported or unauthorized plans.

### 3.5 SOQL Generation and Execution Agent

* Generate or build SOQL from the validated query plan.
* Apply the SOQL safety guard.
* Invoke approved read-only Salesforce or MCP tools.
* Handle structured query errors and bounded repair attempts.
* Never execute an unvalidated model-generated query.

### 3.6 Data Analysis and Auditor Agent

* Validate the shape and types of returned data.
* Calculate totals, averages, rankings, comparisons, and percentages.
* Check for missing values, duplicate records, and invalid denominators.
* Independently verify important calculations.
* Mark results as verified, failed, or partially verified.

### 3.7 Visualization Agent

* Select an appropriate chart or table.
* Use verified result data as the only source of chart values.
* Provide chart titles, axes, labels, and units.
* Return a structured visualization specification.

### 3.8 Insight and Diagnostic Agent

* Explain trends and differences visible in verified results.
* Cite the values and groups supporting each explanation.
* Distinguish observed facts from possible causes.
* Avoid asserting a cause when the available data only shows a correlation or difference.

### 3.9 Orchestrator

* Manage agent execution order and shared state.
* Handle clarification, validation failures, and recoverable errors.
* Limit repair attempts to a configurable maximum of three.
* Stop when authorization fails or the request cannot safely proceed.
* Ensure failed verification prevents unsupported conclusions from being returned.

## 4. Execution Workflow

1. Receive the question and request ID.
2. Authenticate and authorize the request.
3. Interpret the question and identify missing details.
4. Discover and validate relevant Salesforce metadata.
5. Build and validate the structured query plan.
6. Construct the read-only SOQL query.
7. Apply authorization, field permissions, limits, and safety validation.
8. Execute the query through the Salesforce adapter or MCP interface.
9. Validate the returned records.
10. Calculate and independently verify the requested metrics.
11. Build a visualization specification from verified results.
12. Generate evidence-based insights.
13. Save audit and lineage metadata.
14. Return the response, visualization, and verification status.

If a recoverable query error occurs, the system may revise the query plan or query within the configured retry limit. Every retry must repeat the required safety checks.

## 5. Salesforce Integration (Target)

Define a common adapter interface so that the application can use either mock data or a real Salesforce connection.

The adapter should support:

* Describing available objects and fields.
* Retrieving approved metadata.
* Executing validated read-only queries.
* Returning normalized records and structured errors.

The API defaults to an in-memory mock adapter. A Salesforce REST adapter using
OAuth client credentials is available when `SALESFORCE_MODE=live` and the
required backend credentials are configured. Its permissions are those of the
Salesforce user assigned as the Connected App's run-as identity. A future
multi-user application should use an approved per-user identity flow and enforce
application authentication and authorization.

Credentials must be stored in environment configuration or a secret manager, never in source code.

## 6. MCP Tool Contracts

The MCP integration should expose narrowly scoped, validated tools.

### describe_object

Input: approved object name.

Output: accessible fields, field types, and supported relationships.

### execute_soql

Input: validated read-only SOQL and execution limits.

Output: records, query metadata, and execution status.

### search_metadata

Input: a search term or approved metadata criteria.

Output: relevant accessible metadata.

### get_data_lineage

Input: request ID or result reference.

Output: source objects, source fields, transformations, and execution references.

### get_audit_trail

Input: request ID or authorized audit criteria.

Output: relevant audit events, statuses, and verification results.

Each tool must validate its arguments, enforce authorization, limit returned data, and avoid exposing secrets.

## 7. API Request and Response Design

### Example request

```json
{
  "question": "Show total sales by region",
  "session_id": "session-example",
  "filters": {}
}
```

### Example response

```json
{
  "request_id": "request-example",
  "status": "success",
  "answer": "Sales totals grouped by region.",
  "verification": {
    "status": "verified",
    "checks_passed": 3,
    "checks_failed": 0
  },
  "visualization": {
    "type": "bar",
    "title": "Sales by Region",
    "x_field": "region",
    "y_field": "sales_total"
  },
  "data": [],
  "errors": []
}
```

The examples are illustrative API contracts. Production responses must use actual request IDs, validated result data, and truthful verification statuses. The visualization schema should be validated with Pydantic.

## 8. Data Flow and Session State

The shared execution context should track:

* Request ID and session ID.
* Authenticated user and authorized scope.
* Current question and relevant prior questions.
* Structured intent and validated query plan.
* Discovered metadata.
* Generated query and execution metadata.
* Retrieved data or a secure reference to it.
* Calculation outputs and verification results.
* Visualization specification and insight evidence.
* Errors, retry count, and audit references.

For follow-up questions, modify only the relevant part of the prior query state. For example, “Show only the top 5” changes the ranking limit while retaining the relevant filters and metric.

Session state must be scoped to the authorized user. Sensitive records should not be copied into conversation history unnecessarily.

## 9. Security and Permissions

* Authenticate API requests.
* Enforce server-side authorization.
* Apply Salesforce object permissions and field-level security.
* Use an allowlist of supported objects, fields, and operations.
* Permit read-only query execution only.
* Reject mutation statements and unauthorized query constructs.
* Apply row limits, timeouts, and resource limits.
* Redact credentials and sensitive information from logs.
* Protect audit records from unauthorized access.
* Validate generated queries using a proper parser or safe query builder.

A regular-expression check alone is not sufficient to secure arbitrary SOQL.

## 10. Audit and Data Lineage

Each execution should record:

* Request ID and timestamp.
* Authorized user or privacy-preserving user reference.
* Intent and query plan version.
* Source objects and fields.
* Query fingerprint and execution outcome.
* Calculation and verification status.
* Visualization and insight references.
* Retry count and sanitized error details.

Avoid storing complete sensitive records or credentials in audit logs. Define retention and access policies before production deployment.

## 11. Failure Handling and Observability

Return structured error categories, including:

* Invalid request.
* Unsupported question.
* Missing clarification.
* Permission denied.
* Metadata discovery failure.
* Query validation failure.
* Salesforce API failure.
* Verification failure.
* Visualization failure.
* Internal error.

Use structured logs and correlation IDs. Retry only errors that are safe and likely to be recoverable. Never convert an execution failure into a fabricated successful result.

## 12. Deployment Design

### Local development

* FastAPI application.
* Mock Salesforce adapter.
* Local environment configuration.
* Automated pytest suite.

### Container deployment

* Docker image for the application.
* Environment-based configuration.
* Health checks and bounded resource usage.
* Separate test and production settings.

### Azure option

Use an appropriate Azure application hosting service, managed secrets, centralized logging, and approved networking and identity controls.

### AWS option

Use an appropriate AWS application hosting service, Secrets Manager or equivalent, centralized logging, and approved identity and network controls.

The final cloud platform should be selected based on organizational standards, security requirements, cost, and operational capabilities.

## 13. Design Principles

1. Separate LLM interpretation from deterministic execution.
2. Enforce security independently of the LLM.
3. Use structured data contracts between components.
4. Make calculations reproducible and testable.
5. Ground explanations in verified evidence.
6. Preserve query context for follow-up questions.
7. Record sufficient metadata for auditing without exposing sensitive data.
8. Fail safely when permissions, query execution, or verification fail.
