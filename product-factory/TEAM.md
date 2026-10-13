# Product Team — Team Charter

> **File purpose:** Defines the mission, boundaries, operating model, lifecycle, ownership, artifacts, gates, and human-authority rules for the Product Factory Team.

**Team ID:** `product-team`  
**Parent:** `platform-factory`  
**Team Type:** Product Definition & Orchestration Sub-Factory  
**Primary Orchestrator:** `product-lead`  
**Independent Reviewer:** `product-review-routing`  
**Version:** `1.0.0`

## Mission
Transform a business/customer/product initiative into a customer-centered, evidence-based, measurable, testable, traceable, AI-aware, implementation-ready Product Package without forcing downstream teams to invent material product decisions.

## What Product owns
Product owns WHAT should be built, WHY it matters, WHO it serves, expected outcomes, business rules, business access intent, product behavior, acceptance, measurement intent, scope, assumptions, and product decisions.

Product does not own detailed architecture, physical data design, IAM implementation, frontend implementation, API implementation, model/agent implementation, security approval, test execution, AI assurance, deployment, or release approval.

## Agents
| Agent | Primary ownership |
|---|---|
| Product Lead | Intake, initiative classification, scope, orchestration, decisions, integration, change-impact coordination |
| Product Discovery | Personas, needs, pain points/evidence, use cases, persona→feature and persona→data-access mappings |
| Requirements | PDR/PRD, capabilities, features, requirements, acceptance criteria, product-side PRTM |
| Workflow & Journey | Journeys, workflows, exceptions, AI/agent→UI feature mapping |
| AI Product Strategy | AI suitability, AI use cases, autonomy, HILT, Human/System/AI responsibility |
| Product Analytics | KPIs, events, measurement plan, post-release outcome loop |
| Product Review & Routing | Independent review, gate evidence, consistency, impact validation, handoff readiness, downstream routing |

## Supported initiative paths
- `NEW_PRODUCT`: full path.
- `NEW_CAPABILITY`: delta path against approved baseline.
- `PRODUCT_CHANGE`: delta path against approved baseline.
- `DEFECT`: triage/fast path; escalate to Product Change only when product definition must change.

## Evidence states
`VALIDATED`, `PARTIALLY_VALIDATED`, `ASSUMPTION`, `HYPOTHESIS`, `UNKNOWN`, `DECISION`.

## Product decomposition
Business Objective → Product Outcome → Persona → Pain Point/User Need → Use Case → Capability → Feature → Workflow/AI Capability → Responsibility → Requirement → Acceptance Criteria → KPI/Test → Release Evidence.

## Authoritative artifacts
The PDR/PRD is the human-readable integrated product definition. Structured YAML artifacts remain authoritative for machine processing. The PRTM is a living lifecycle traceability view/graph and may be extended downstream by authorized factories.

## Access-model boundary
Product defines WHO needs access to WHAT business object, for WHICH actions, under WHAT business scope and WHY. Security/IAM determines HOW identity, roles, attributes, relationships, policies, claims, enforcement and audit implement those requirements.

## Human authority
Agents may discover, structure, analyze, challenge, propose options, detect gaps, and maintain traceability. Humans retain authority for material business objectives, major scope tradeoffs, consequential product behavior, risk acceptance, policy decisions, and explicit overrides.

## Product readiness
The team must not advance work merely because files exist. Applicable artifacts must be coherent, traceable, sufficiently complete, and consumable by downstream teams. Missing material decisions are surfaced rather than invented.

## Definition of Done
A Product Team initiative is complete when:
- applicable initiative path is executed;
- evidence/assumptions/unknowns are explicit;
- applicable personas, needs, pain points, use cases, capabilities and features are defined;
- requirements and acceptance criteria are testable;
- workflows and material exceptions are defined;
- AI/HILT/responsibility mappings are complete when applicable;
- persona feature and data-access mappings are complete when applicable;
- KPIs/events are defined when measurement is required;
- change/defect/release impact is assessed when applicable;
- PRTM is current;
- independent Product Review is complete;
- downstream routing and handoff readiness are recorded;
- unresolved blockers are not hidden.
## Mandatory orchestration compatibility
This factory implements `FORWARD`, `BACKWARD`, `PARALLEL`, `CONDITIONAL`, `REWORK`, and `ESCALATION` through the machine-readable `orchestration/` contract. All transitions must be auditable and preserve checkpoints/traceability.

## AI-PDLC initiative coverage
The Product Factory supports brand-new products, capabilities and features; general product changes; defects found during development; and defects returned from operations. Operational defects enter through the defect path with production evidence and may route backward into Product definition, Engineering, Testing, Assurance, Observability and Release as impact requires.

## Canonical peer-factory interoperability
Product Factory routes mature product definition to the canonical peer factories defined in `../platform/ai-pdlc-factory-topology.yaml`. Cross-cutting factories may participate conditionally and in parallel throughout the lifecycle. Shared Assets & Registries is a governed common platform consumed by all factories.
