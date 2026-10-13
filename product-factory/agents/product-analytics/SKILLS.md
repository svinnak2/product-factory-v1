# Product Analytics & KPI Agent — Skills
> **File purpose:** Procedures for outcomes, KPIs, product events, baselines and post-release measurement.

## Outcome model
Define business, user, adoption, workflow, quality, AI and operational metrics as applicable. Connect measurable pain-point baselines to intended product outcomes.

Each KPI should capture ID, question/outcome, definition, calculation, unit, source, population/dimensions, baseline, target if approved, owner and reporting expectation.

Never invent targets. Use `TBD` or `NOT_MEASURED` with a decision/measurement owner.

## Product events
Use stable event semantics such as `<domain>.<object>.<action>`. Define event purpose, trigger, required properties and privacy constraints. Product events express measurement intent; Observability owns technical telemetry implementation.

## Post-release loop
Release → production evidence → KPIs/user feedback/AI metrics → Product Analytics → Product Lead → new initiative or corrective action.

## Change review
For existing-product work, identify KPIs/events affected by changed behavior and whether baselines need preservation or redefinition.
