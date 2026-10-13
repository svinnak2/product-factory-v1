# AI-PDLC-Platform
> **Purpose:** Repository root for the AI Product Development Life Cycle platform, all lifecycle/cross-cutting factories, shared contracts, policies, orchestration, registries and platform definitions.

## Current contents
- `product-factory/` — Product Factory implementation.
- `contracts/` — cross-factory interface contracts.
- `platform/` — canonical topology/platform definitions.
- `orchestration/` — shared orchestration contract/event schema.
- `policies/` — platform security and secure-development policy baseline.
- `registries/` — shared governed registry location.
- `.github/` — repository-level automation.

Future peer factories should be added directly under this root using the canonical topology IDs.


## Human-in-the-loop runtime model (v5)
Product initiatives enter through `intake/`. All human communication uses `human-interface/`. Product Factory continuously emits meaningful stage/task status, alerts on uncertainty/problems, pauses on blockers/decisions/approvals, and requires human approval for governed outputs. `cli/` provides the reference terminal channel; a web console/API should reuse the same protocol rather than reimplement factory logic.

Development context terminology is `PRODUCT_CREATION` and `PRODUCT_EVOLUTION`.


## Executable Product Factory (v6)
`runtime/` provides the executable state machine, model-adapter boundary, durable local pilot stores, artifact validation and completion profiles. `cli/ai_pdlc.py` can now start, execute, pause, review, rework, answer and resume Product Factory workflows. Production model execution requires an explicitly configured approved model endpoint; no model/vendor/secrets are hard-coded.
