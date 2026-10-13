# AI-PDLC Platform Intake
> **Purpose:** Authoritative entry point for initiatives submitted by humans or approved upstream systems.

Product initiatives are submitted here and validated against `product-initiative.schema.json`. The platform then routes Product initiatives to `product-factory`.

## Development context terminology
- `PRODUCT_CREATION` — creation of a new product/application/product experience. It may still reuse shared platform assets.
- `PRODUCT_EVOLUTION` — change to an existing product baseline, including capabilities, features, product changes and defects.

These terms replace Greenfield/Brownfield throughout this platform.

## Submission
Recommended CLI:
`python cli/ai_pdlc.py product start intake/examples/medical-appeals.yaml`

Production systems may submit the same schema through a future API or web console. Channels must not change orchestration semantics.
