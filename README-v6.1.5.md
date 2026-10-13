# AI-PDLC Product Factory v6.1.5

v6.1.5 adds governed **BACKWARD orchestration** for Product Definition blockers discovered by independent Product Review.

## Why

`retry` is appropriate for provider/runtime failures or regeneration with corrected context. It is not the right mechanism when Product Review finds missing Product-owned business semantics. v6.1.5 routes those gaps back to Product Discovery and Workflow, asks the Product Owner only for material decisions that agent authority cannot make, persists resolution provenance, and then returns automatically to the blocked artifact for governed regeneration and review.

## New command

```bash
python cli/ai_pdlc.py product resolve-blockers \
  INIT-EVENT-PLANNER-001 \
  --session RUN-20261004-100903
```

Optional `--artifact PRD` restricts selection to a particular blocked artifact. The command only consumes unresolved `QUALITY_REVIEW_FAILED` alerts containing structured `PRODUCT_DEFINITION_GAP` findings with `blocks_product_definition=true`.

## Runtime behavior

1. Builds a persisted BACKWARD resolution plan from the independent review findings.
2. Preserves dependency identifiers such as `DEP-PRD-001` when present.
3. Routes each blocker to Product Discovery and/or Workflow based on structured finding ownership/routing.
4. Uses approved upstream artifacts and immutable approval envelopes as evidence.
5. Requests one targeted Product Owner decision at a time only when a material Product decision is required.
6. Records answers in the existing append-only human interaction audit ledger with `asked_at`, `answered_at`, blocker and artifact provenance.
7. Stores resolution records under `.runtime/sessions/<initiative>/<session>/resolutions/<artifact>/`.
8. Marks only the source quality alert resolved after every Product Definition blocker is resolved.
9. Adds resolved definitions to the Agent Context Package for the blocked artifact.
10. Returns automatically to Requirements/PRD regeneration and independent Product Definition review.

## Resolution files

```text
resolutions/
└── PRD/
    ├── resolution-plan.json
    ├── DEP-PRD-001.json
    ├── DEP-PRD-002.json
    ├── DEP-PRD-003.json
    └── DEP-PRD-004.json
```

The resolver response is validated against `product-factory/schemas/product-definition-resolution.schema.json`.

## Existing command boundaries

- `continue` / `resume`: normal forward execution.
- `retry`: retry a recoverable generation/provider/schema/quality operation after the underlying cause is corrected.
- `changes`: human-requested artifact rework.
- `answer`: answer the current targeted human decision; during BACKWARD resolution it resumes the same blocker automatically.
- `input`: general human business input/audit record.
- `resolve-blockers`: structured BACKWARD resolution of Product-owned Product Definition gaps.

## Safety and governance

- Approved artifacts are not silently edited.
- The resolver does not make Architecture, Security enforcement, Engineering, infrastructure, database, or other downstream technical decisions.
- Human silence is never approval.
- Existing approved artifacts, approval records, events and audit history remain intact.
- Resolution artifacts supplement approved evidence; the regenerated governed Product artifact still requires independent review and human approval.
