# AI-PDLC Platform v6.1

v6.1 is a production-oriented executable Product Factory reference implementation. It accepts a Product Initiative, isolates each execution in a run/session workspace, invokes a configured model adapter, performs JSON Schema validation and independent Product Review quality checks, pauses for human approval, incorporates human rework feedback, and produces versioned JSON plus Markdown artifacts.

## Production boundary
Workflow controls can enforce structure, traceability, review and validation, but generated business content still depends on authoritative inputs and accountable human approval. v6.1 therefore never treats model output as automatically approved.

## Codex
The `codex` adapter invokes the supported Codex CLI in a read-only sandbox and relies on supported Codex authentication. It does not scrape or reuse VS Code extension tokens.

```bash
codex --version
codex
python cli/ai_pdlc.py product start intake/examples/consumer-event-planner.yaml --adapter codex
```

Each run is stored under `.runtime/sessions/<initiative>/<RUN-id>/`.
