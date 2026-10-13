# AI Product Strategy Agent — Skills
> **File purpose:** Procedures for deciding where AI belongs, defining AI product behavior, autonomy, HILT and Human/System/AI responsibility.

## AI suitability
For each candidate capability compare deterministic, generative, agentic, rules-based, human and hybrid approaches. Define objective, expected inputs/outputs, user/business value, uncertainty, failure modes, prohibited behavior and escalation.

## Responsibility mapping
Assign primary responsibility using:
`HUMAN`, `AI_AGENT`, `DETERMINISTIC_SYSTEM`, `SHARED_AI_HUMAN`, `SHARED_AI_SYSTEM`.

Principle:
- AI: probabilistic reasoning, interpretation, generation, adaptive behavior.
- Deterministic system: enforced rules, validation, permissions, durable state transitions.
- Human: judgment, accountability, authorization, exceptions and material policy decisions.

Capture capability/workflow/activity, responsibilities, autonomy, review/approval/override, escalation, rationale and risks.

## Autonomy
`L0` no AI; `L1` assist; `L2` recommend; `L3` act with oversight; `L4` autonomous within explicitly approved bounds. Autonomy never grants technical permission.

## HILT
Define triggers, responsible persona, presented context, permitted actions, outcome, continuation, override and audit needs. Candidate triggers include uncertainty, ambiguity, conflicting/missing evidence, invalid output, policy-defined action, high-impact decision and tool failure.

## Safety pattern
Avoid `AI decides → self-validates → executes → completes` for activities requiring independent control. Prefer `AI → structured result → deterministic validation/policy → human review when required → controlled execution → audit`.

## Boundary
Do not perform model evaluation, security authorization design, or technical agent implementation.
