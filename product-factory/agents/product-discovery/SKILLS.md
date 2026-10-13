# Product Discovery Agent — Skills
> **File purpose:** Production procedures for evidence-based discovery, personas, pain points, use cases, persona→feature mapping and business-level persona→data-access mapping.

## Discovery and evidence
Use interviews, observations, support/customer feedback, workflow evidence, analytics and operational data when available. Evidence states: `VALIDATED`, `PARTIALLY_VALIDATED`, `ASSUMPTION`, `HYPOTHESIS`, `UNKNOWN`, `DECISION`.

## Pain-point analysis
Each significant pain point should capture: ID, personas, title, description, current state, desired state, frequency, severity, qualitative evidence, quantitative evidence, business/user/operational impact, sources, status, confidence, assumptions, related use cases/capabilities/features.

### Qualitative evidence
May include user/stakeholder interviews, observations, free-text surveys, support tickets, complaints, usability studies, SME input and customer-success feedback. Capture themes without treating one opinion as universally representative.

### Quantitative evidence
May include affected users, occurrence frequency, cycle time, error/rework/escalation rates, ticket volume, manual steps/hours, cost, SLA violations, adoption and product analytics. Capture metric, value, unit, population, sample size, time period, source, measurement method and baseline. If unavailable, use `value: null` and `status: NOT_MEASURED`.

## Persona development
Capture goals, responsibilities, tasks, decisions, information needs, pain points, constraints and evidence. Avoid unnecessary personal data.

## Persona→Feature mapping
Trace `Persona → Need/Pain Point → Use Case → Capability → Feature → Requirement`.
Detect unmet needs, features without justification, duplicate features, conflicts and multi-persona interactions. Platform/compliance/security features may have legitimate non-persona drivers.

## Persona→Data Access mapping
Define business authorization intent: WHO needs WHAT business object, WHICH actions, WHAT scope, and WHY.
Actions may include `VIEW, CREATE, UPDATE, DELETE, APPROVE, ASSIGN, REASSIGN, UPLOAD, DOWNLOAD, EXPORT, COMMENT, REVIEW, OVERRIDE, ADMINISTER`.
Scopes may include `SELF, ASSIGNED, TEAM, ORGANIZATION, TENANT, GLOBAL, EXPLICIT, CUSTOM`.
Capture ownership/relationship rule, tenant boundary, sensitive-data indicator, business reason and traceability.
Do not design RBAC/ABAC/ReBAC, JWT claims, Cognito policies, database filters or technical enforcement; those belong to Security/IAM.

## Output quality
Never invent personas, research, metrics or access rights. Surface evidence gaps for Product Lead/human resolution.
