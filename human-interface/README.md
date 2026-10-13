# Human Interface
> **Purpose:** Platform-wide human/factory communication protocol. CLI, web and API channels must use the same interaction events and decisions.

The protocol implements:
1. continuous workflow/stage/task updates;
2. warnings and alerts;
3. explicit requests for missing information;
4. pause/resume when blocking information or decisions are missing;
5. human review and approval of every governed Product Factory output;
6. recorded feedback, rejection, rework and reapproval;
7. auditable interaction history.

The Product Lead is the Product Factory's human-facing orchestration authority. Specialist agents emit status/results to the Product Lead rather than creating incompatible human interaction patterns.
