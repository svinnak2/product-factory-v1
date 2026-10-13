# AI-PDLC Cross-Factory Contracts
> **Purpose:** Platform-level interoperability contracts between factories. These contracts are intentionally outside individual factories because multiple factories must consume them.

Product-originated contracts currently define the minimum information Product Factory provides to canonical peer factories. Future factories should add their own inbound/outbound contracts here using stable IDs and schema versions.

Rules:
- A contract defines an interface, not ownership transfer.
- Consumers must not silently invent material upstream decisions.
- Missing required information routes backward/remediation to the authoritative owner.
- Contract changes require compatibility review and versioning.
