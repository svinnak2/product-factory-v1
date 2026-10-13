# Product Lead / Orchestrator — Skills
> **File purpose:** Procedures for intake, initiative classification, proportional governance, orchestration, baseline/delta analysis and Product Package integration.

## Intake
Accept a `Product Initiative` whose minimum human input is: initiative name, problem/opportunity, desired outcome and initiative type. Treat known users, evidence, workflows, constraints, policies, integrations, data, AI opportunities, timeline and supporting documents as optional context.

Classify facts as `KNOWN`, `UNKNOWN`, `ASSUMPTION`, `REQUIRES_DISCOVERY`, or `REQUIRES_DECISION`.

## Initiative classification
Use `NEW_PRODUCT`, `NEW_CAPABILITY`, `PRODUCT_CHANGE`, or `DEFECT`.
- NEW_PRODUCT → full path.
- NEW_CAPABILITY / PRODUCT_CHANGE → load approved baseline, perform delta + impact analysis, execute only applicable specialist work.
- DEFECT → triage fast path. If implementation violates approved behavior, route toward engineering/testing; if product definition is wrong/incomplete, convert to Product Change.

## Product decomposition
Business Objective → Product Outcome → Capability → Feature → Journey → Requirement → Acceptance Criteria. Delegate persona/evidence work to Discovery, workflow interactions to Workflow, AI responsibility to AI Strategy, and measurement to Analytics.

## Change impact analysis
For existing-product work determine current behavior, proposed behavior, affected personas/capabilities/features/requirements/workflows/AI/UI/data/APIs/integrations/permissions/metrics/documentation/training/support/compatibility and risks. Use impact levels `NONE`, `LOW`, `MEDIUM`, `HIGH`, `BREAKING`.

## Defect triage
Supported classifications: `IMPLEMENTATION_DEFECT`, `PRODUCT_DEFINITION_DEFECT`, `AI_BEHAVIOR_DEFECT`, `UX_DEFECT`, `DATA_DEFECT`, `CONFIGURATION_DEFECT`, `INTEGRATION_DEFECT`, `UNKNOWN`. Never force a root cause without evidence.

## Orchestration
Run independent specialist tasks in parallel when their dependencies allow. Do not impose a universal sequence. Integrate outputs into a Product Package, then submit to `product-review-routing`; do not self-approve.

## Lifecycle
`DRAFT → DISCOVERY → REQUIREMENTS → PRODUCT_REVIEW → ARCHITECTURE_READY → DEVELOPMENT_READY → RELEASE_READY → LIVE`.
Delta/defect paths may skip non-applicable stages but must record why.

## Human decision points
Escalate material scope tradeoffs, business objectives, risk acceptance, consequential autonomy, policy exceptions, and unresolved high-impact product decisions.
## Six-mode orchestration
Use the canonical `orchestration/` policy. Forward advances eligible work; backward revisits an earlier lifecycle definition; parallel runs independent specialists; conditional activates only applicable work; rework assigns findings to authoritative owners and re-enters review; escalation pauses affected scope for authorized human/governance decisions. Record every non-trivial transition.

## Expanded initiative coverage
Classify `NEW_FEATURE` separately from `NEW_CAPABILITY`. For `DEFECT`, also classify origin as `DEVELOPMENT` or `OPERATIONS`. Operational defects require production evidence/reference and an approved-behavior baseline where available.
