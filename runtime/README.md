# Executable AI-PDLC Runtime
> **Purpose:** Executes factory workflows from machine-readable definitions while keeping models, storage and user channels replaceable.

The v6 Product Factory runtime:
- validates Product Initiative intake;
- chooses Product Creation or Product Evolution completion profile;
- executes the seven Product agents through an adapter;
- maintains durable local state/event/artifact/approval stores;
- validates structured artifact envelopes;
- pauses on missing blocking information and every governed artifact;
- resumes after human input/approval;
- supports rework/rejection;
- performs final independent Product Review & Routing;
- declares completion only when the machine-readable completion gate passes.

`MockAdapter` is deterministic and exists for smoke/integration testing only. `OpenAICompatibleAdapter` is a provider-neutral HTTP adapter configured entirely by environment variables. No provider key/model/endpoint is hard-coded.
