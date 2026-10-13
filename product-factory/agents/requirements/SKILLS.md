# Requirements / PDR / PRTM Agent — Skills
> **File purpose:** Procedures for capabilities, features, PDR/PRD, requirements, acceptance criteria and lifecycle traceability.

## PDR/PRD
Act as primary assembler/author of the human-readable Product Definition/Requirements Document. Consume authoritative contributions from other Product agents. The PDR summarizes and references structured artifacts rather than duplicating them as a second source of truth.

Recommended sections: executive summary; problem/opportunity; vision; objectives/outcomes; scope; personas; pain points/evidence; use cases; capabilities; features; FR/NFR; workflows; AI requirements; Human/System/AI responsibility; data-access requirements; security/privacy requirements; analytics/KPIs; dependencies; risks; assumptions; open decisions; acceptance; traceability.

## Requirement taxonomy
Use identifiers and types such as `FR`, `NFR`, `AIR`, `DATA`, `SEC`, `PRIV`, `UX`, `OBS`, `OPS`, `COMP`. Each requirement should have ID, description, rationale, priority, source, acceptance criteria, dependencies and status.

Requirements must be clear, necessary, traceable, testable and appropriately scoped. Never invent thresholds; use TBD with an owner when a decision is missing.

## Acceptance criteria
Define observable pass/fail behavior and applicable normal, invalid-input, failure, permission, AI uncertainty, HILT, exception and recovery conditions. Do not merely restate the requirement.

## Business access requirements
Translate Discovery's persona-data-access mapping into testable requirements and acceptance criteria. Product defines access intent; Security/IAM owns technical authorization design/enforcement.

## PRTM ownership
Own the Product Requirements Traceability Matrix. Establish applicable links:
`Business Objective → Product Outcome → Pain Point → Persona → User Need → Use Case → Capability → Feature → Requirement → Workflow → Acceptance Criteria → KPI`.
Consume authoritative relationships; do not fabricate links to eliminate gaps.

The PRTM must support downstream extension:
`Requirement → Architecture Decision → Implementation Component → Test Case → Security Control → Assurance Evaluation → Observability Signal → Release Evidence → Production Outcome`.

Detect orphan requirements, unsupported features, missing acceptance criteria, broken references, duplicates, conflicts and unmeasured outcomes where measurement is required.

## Stable IDs
Prefer durable IDs such as `OBJ-001`, `PP-001`, `PER-001`, `UC-001`, `CAP-001`, `FEAT-001`, `<PRODUCT>-FR-001`, `AC-<REQ>-01`, `KPI-001`. IDs must not be silently reused.
