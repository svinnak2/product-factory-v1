# AI-PDLC Platform v6.1.4 Hardening

This release hardens Product Factory quality semantics, runtime failure classification, targeted recovery, context provenance, status visibility, and human-interaction auditability.

## Key changes
- Product Definition Readiness is evaluated separately from Implementation Readiness.
- Downstream technical dependencies no longer automatically fail a Product artifact when ownership/routing is explicit.
- Provider timeout/unavailable, schema validation, quality review, generation, and human-decision failures are classified separately.
- Retry resolves only the active artifact blocker.
- Compact Agent Context Package supplies direct approved dependencies plus upstream approval provenance.
- Every human artifact approval is timestamped in the authoritative approval and append-only human interaction ledger.
- Human answers and substantive business inputs are timestamped and auditable; change requests/rejections stay in their existing audit paths.
- Question records preserve asked_at and answered_at.
- `product input`, `product audit`, and `product audit-backfill` commands are available.

## Existing-session migration
Run `python cli/ai_pdlc.py product audit-backfill <initiative> --session <RUN-id>` once to seed the new ledger from historical APPROVED decisions and stored human clarifications.
