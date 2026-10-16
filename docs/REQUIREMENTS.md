# Requirements Analysis — Agentic AI Salesforce Data Analytics & Visualization Assistant

## 1. Project Objective

The objective is to build an AI-powered application that enables business users and financial auditors to analyze Salesforce data using natural-language questions.

The application translates a user's question into a structured query plan, discovers relevant Salesforce metadata, retrieves data using safe read-only SOQL, performs deterministic calculations, verifies results, and generates appropriate visualizations and evidence-based insights.

The system must not invent results or allow the language model to bypass security controls.

## 2. Project Scope

### In scope

* Natural-language query interpretation.
* Salesforce object, field, and relationship discovery.
* User permissions and field-level security enforcement.
* Safe, read-only SOQL generation and execution.
* Deterministic aggregation and calculation.
* Result verification and data-quality checks.
* Charts and tables with evidence-based explanations.
* Follow-up questions using conversation context.
* Audit records and data lineage.
* Automated testing, CI/CD, and cloud deployment.

### Out of scope for the initial version

* Creating, updating, or deleting Salesforce records.
* Autonomous business actions.
* Predicting business outcomes without an explicitly implemented model.
* Accessing objects or fields that the current user is not authorized to read.

## 3. Functional Requirements

| ID    | Requirement                    | Acceptance criteria                                                                |
| ----- | ------------------------------ | ---------------------------------------------------------------------------------- |
| FR-01 | Natural-language understanding | A supported question becomes a structured intent and query plan.                   |
| FR-02 | Schema discovery               | The system identifies permitted objects and fields from metadata.                  |
| FR-03 | Safe SOQL                      | Unauthorized objects, unauthorized fields, and mutation operations are rejected.   |
| FR-04 | Data analysis                  | Calculated totals match deterministic calculations on the test fixture.            |
| FR-05 | Visualization                  | Chart values match the verified result.                                            |
| FR-06 | Follow-up questions            | “Show only the top 5” preserves relevant prior filters and metrics.                |
| FR-07 | Audit and lineage              | Each execution has a traceable request ID, source fields, and verification status. |
| FR-08 | Error handling                 | Invalid or unsupported questions return clear, structured errors.                  |
| FR-09 | Insight generation             | Explanations are grounded in retrieved and verified data.                          |
| FR-10 | Salesforce integration         | Data is retrieved through an authenticated, permission-aware Salesforce adapter.   |

## 4. Non-Functional Requirements

| ID     | Requirement     | Acceptance criteria                                                                               |
| ------ | --------------- | ------------------------------------------------------------------------------------------------- |
| NFR-01 | Security        | Credentials and sensitive records are not leaked through logs or responses.                       |
| NFR-02 | Reliability     | Failures return structured errors rather than fabricated results.                                 |
| NFR-03 | Testability     | Unit, integration, security, and end-to-end tests are automated.                                  |
| NFR-04 | Maintainability | API, agents, orchestration, Salesforce integration, analysis, and security have separate modules. |
| NFR-05 | Performance     | Query execution has configurable timeouts and result limits.                                      |
| NFR-06 | Observability   | Requests have traceable IDs, execution status, and useful diagnostic logs.                        |
| NFR-07 | Reproducibility | Deterministic calculations can be repeated against the same input data.                           |

## 5. Supported User Queries

Initial supported queries include:

1. Show total sales by region.
2. Show the top sales representatives by revenue.
3. Show monthly revenue.
4. Compare this year's revenue with last year's revenue.
5. Show the opportunity pipeline by stage.
6. Find opportunities above $100,000.
7. Show the top customers by revenue.
8. Find customers with no recent activity.
9. Show lead conversion rate by lead source.
10. Identify sales representatives below their targets.

Each query type must define its required Salesforce objects, fields, filters, calculations, and visualization.

## 6. Business Definitions

Business metrics must be defined explicitly before implementation.

* **Sales revenue:** Revenue recognized under the organization's agreed reporting definition.
* **Pipeline amount:** Amount associated with opportunities that meet the organization's pipeline inclusion criteria.
* **Closed-won revenue:** Amount from opportunities whose stage is Closed Won, subject to the organization's reporting rules.
* **Lead conversion rate:** Converted leads divided by the agreed eligible lead population, multiplied by 100.
* **Year-over-year change:** Current-period metric minus prior-period metric.
* **Year-over-year percentage change:** Difference divided by the prior-period metric, multiplied by 100. If the prior-period metric is zero, return a clearly defined not-applicable result instead of dividing by zero.

These definitions must be validated with business stakeholders. Salesforce fields and stage values may differ between organizations.

## 7. Assumptions and Constraints

* Salesforce is the primary business data source.
* The initial version uses mock data for development and testing.
* Real Salesforce integration uses authenticated API access.
* The application respects object permissions and field-level security.
* The LLM interprets requests but does not enforce security.
* Calculations and verification use deterministic code.
* Only read-only analytics are supported.
* Results depend on the completeness and quality of source data.

## 8. Dependencies and Open Questions

* Which Salesforce objects and custom fields are available?
* Which OAuth flow is approved for the deployment?
* Which LLM provider and model will be used?
* Which MCP server and tools will expose Salesforce operations?
* What are the official definitions of revenue, pipeline, and conversion?
* What are the data retention and audit retention policies?
* Will the frontend use React or another framework?
* Will deployment use Azure or AWS?
* What are the expected user volume, query limits, and latency targets?

## 9. Risks and Mitigations

| Risk                          | Mitigation                                                                        |
| ----------------------------- | --------------------------------------------------------------------------------- |
| Incorrect SOQL                | Build queries from validated structured plans and validate them before execution. |
| Unauthorized data access      | Enforce server-side authorization, object permissions, and field-level security.  |
| Incorrect calculations        | Use deterministic calculation functions and independent verification tests.       |
| Hallucinated insights         | Generate explanations only from verified result evidence.                         |
| Salesforce API failures       | Add timeouts, structured errors, and bounded retries where appropriate.           |
| Ambiguous questions           | Ask a clarification question instead of guessing.                                 |
| Sensitive information in logs | Redact credentials and sensitive field values.                                    |
| Broken follow-up context      | Store explicit query state and validate changes to filters and metrics.           |

## 10. Acceptance Criteria

The initial version is acceptable when:

1. A supported natural-language question can be converted into a structured query plan.
2. Mock Salesforce data can be retrieved through a defined adapter.
3. Invalid or unauthorized queries are rejected before execution.
4. Deterministic calculations produce expected results on known test data.
5. The verification component detects intentionally incorrect results.
6. Chart data matches verified analytical results.
7. Follow-up questions preserve applicable filters and metrics.
8. Execution records include request ID, query metadata, and verification status.
9. Automated unit, integration, and security tests pass.
10. The application documents how to configure and run the mock environment.
