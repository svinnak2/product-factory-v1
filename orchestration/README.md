# AI-PDLC Platform Orchestration
> **Purpose:** Shared orchestration semantics and event contract consumed by all factories.

Every factory must support FORWARD, BACKWARD, PARALLEL, CONDITIONAL, REWORK and ESCALATION. Factory-specific transition/routing rules remain inside that factory; the shared parent contract and event schema live here.
