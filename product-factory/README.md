# Product Factory Team

Production-ready Product Definition & Orchestration sub-factory for an AI Product Development Life Cycle (AI-PDLC).

## Purpose
This factory accepts a human **Product Initiative** and converts it into a reviewed, traceable, measurable, implementation-ready **Product Package** for downstream factory teams.

It supports:
- `NEW_PRODUCT` — full product-definition path.
- `NEW_CAPABILITY` — delta path for new capabilities/features.
- `PRODUCT_CHANGE` — delta path for changes to an existing product.
- `DEFECT` — proportional fast-path with defect triage.

## Core operating model
Human Initiative → Product Lead → Discovery / Requirements / Workflow / AI Strategy / Analytics → Product Review & Routing → Product Readiness/Change Gate → Downstream factory handoffs.

## Seven agents
1. Product Lead / Orchestrator
2. Product Discovery
3. Requirements / PDR / PRTM
4. Workflow & Journey
5. AI Product Strategy
6. Product Analytics & KPI
7. Product Review & Routing

## Important boundaries
- Product owns **what, why, who, expected outcome, business access intent, and acceptance**.
- Architecture/Data/Security/Engineering own technical design and implementation.
- Product defines persona-level data-access requirements; Security/IAM defines and enforces the authorization mechanism.
- Product Review evaluates product-definition quality; AI Assurance evaluates implemented AI/agent behavior.
- Documentation & Enablement and Change Management are downstream peer factories, not responsibilities hidden inside Product.

## Integration
1. Place this folder under `platform-factory/product-team/` (or rename it to your preferred team ID).
2. Point the parent factory registry/harness to `registry.yaml`.
3. Provide a Product Initiative conforming to `schemas/product-initiative.schema.json`.
4. Use `intake/intake-rules.yaml` and `routing/routing-rules.yaml`.
5. Validate artifacts against `schemas/`.
6. Apply `gates/` before downstream handoff.
7. Consume the handoff contracts under `contracts/`.

## Configuration note
This package is production-oriented but platform-neutral. MCP server names, model IDs, repository paths, CI commands, identity-provider details, and organization-specific policy references must be bound by the parent harness/environment rather than hard-coded here.
## AI-PDLC lifecycle compatibility
This package now explicitly supports `NEW_PRODUCT`, `NEW_CAPABILITY`, `NEW_FEATURE`, `PRODUCT_CHANGE`, and `DEFECT`. Defects distinguish `DEVELOPMENT` from `OPERATIONS`.

It implements the six mandatory orchestration modes: **forward, backward, parallel, conditional, rework, escalation**. The same contract should be adopted by every peer factory at the AI-PDLC parent level; cross-factory orchestration remains a parent-factory concern.

## Canonical AI-PDLC topology
This package uses the normative factory IDs in `../platform/ai-pdlc-factory-topology.yaml`. Product routing occurs at factory level; domain-specific internal agents remain implementation details. Shared Assets & Registries is consumed as a shared capability rather than treated as a lifecycle handoff destination.


## Repository placement (v4)
This factory resides at `AI-PDLC-Platform/product-factory/`. Its seven agents are under `agents/`. Cross-factory contracts, topology, shared orchestration and security policies are intentionally located at the platform root and referenced relatively.


## Interactive execution model (v5)
The Product Lead follows `orchestration/human-interaction-policy.yaml`. Every governed output follows `artifact-lifecycle.yaml` and `approval-gates.yaml`; human approval is version-bound and material changes require reapproval. Blocking missing information creates a checkpoint and pauses execution. Product context is classified as `PRODUCT_CREATION` or `PRODUCT_EVOLUTION`.
