# Parent AI-PDLC Orchestration Contract
> **File purpose:** Integration requirements the parent AI Product Development Life Cycle factory should implement so every sub-factory behaves consistently.

## Required modes for every factory
Every registered factory MUST declare and implement: FORWARD, BACKWARD, PARALLEL, CONDITIONAL, REWORK, ESCALATION.

## Required initiative coverage
The parent AI-PDLC intake/routing model MUST support NEW_PRODUCT, NEW_CAPABILITY, NEW_FEATURE, PRODUCT_CHANGE, and DEFECT with defect origin DEVELOPMENT or OPERATIONS.

## Cross-factory semantics
- FORWARD: advance to eligible downstream factory/gate.
- BACKWARD: return to an earlier factory/stage because upstream definition/evidence must change.
- PARALLEL: dispatch independent factories concurrently and join at declared dependency.
- CONDITIONAL: route only when impact/risk/rules require the factory.
- REWORK: send a failed artifact/control/evaluation back to its authoritative owner and re-enter the same gate/review.
- ESCALATION: suspend affected scope for human/policy/risk authority, then resume from checkpoint.

## Operational bug return loop
Production/operations signal → defect intake → classify origin OPERATIONS → establish expected behavior/baseline → determine Product/implementation/AI/data/UX/config/integration classification → conditionally route affected factories → test/assurance as applicable → release → production → observe outcome.

## Note
This Product Factory package can participate in the contract immediately. Peer factories must implement the same parent contract; this repository cannot make absent peer factories compliant by itself.
