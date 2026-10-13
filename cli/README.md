# AI-PDLC Product Factory CLI
## Production/model mode
Configure an approved OpenAI-compatible model endpoint without committing secrets:
- `AI_PDLC_MODEL_ENDPOINT`
- `AI_PDLC_MODEL_API_KEY`
- `AI_PDLC_MODEL_NAME`
- optional `AI_PDLC_MODEL_TIMEOUT`

Then:
`python cli/ai_pdlc.py product start intake/examples/medical-appeals.yaml`

The runtime generates one governed output, stores it, and pauses for human review.

## Human actions
- `python cli/ai_pdlc.py product status <initiative-id>`
- `python cli/ai_pdlc.py product artifact <initiative-id> <ARTIFACT_TYPE>`
- `python cli/ai_pdlc.py product approve <initiative-id>`
- `python cli/ai_pdlc.py product changes <initiative-id> "requested changes"`
- `python cli/ai_pdlc.py product reject <initiative-id> "reason"`
- `python cli/ai_pdlc.py product answer <initiative-id> "answer to blocking question"`
- `python cli/ai_pdlc.py product continue <initiative-id>`

## Integration-test mode
`--adapter mock` exercises orchestration without an external model. Mock output MUST NOT be treated as product analysis.

Production deployments should replace local JSON storage with an approved durable database/object store while preserving the same state/event/artifact/approval contracts.
