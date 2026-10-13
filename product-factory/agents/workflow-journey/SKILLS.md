# Workflow & Journey Agent — Skills
> **File purpose:** Procedures for product journeys, workflows, exceptions and AI/agent→UI feature mapping.

## Workflow model
Model `Trigger → Preconditions → User Action → System Action → Decision → AI Action → Human Review → Outcome`. Tag actors as `[USER]`, `[SYSTEM]`, `[AGENT]`, `[HILT]`.

Define normal path, material alternate paths, failure paths, completion state, retries/recovery and escalation where relevant.

## AI/Agent→UI mapping
Trace `AI Capability → AI Action → Product Workflow → Persona → Interaction → UI Product Feature`.
Interaction types: `INVISIBLE, INFORM, RECOMMEND, REVIEW, APPROVE, EDIT, OVERRIDE, ESCALATE, COLLABORATE`.
Capture agent/capability/action, workflow, persona, feature, interaction type, AI output, displayed information, user action, approval/edit/override requirements, confidence-display need, failure behavior and HILT requirement.

Potential AI states: `NOT_STARTED, QUEUED, PROCESSING, COMPLETED, REQUIRES_REVIEW, FAILED, CANCELLED`.

## Boundary
Define product interaction behavior, not screen layout, visual design, React implementation or detailed technical orchestration.
