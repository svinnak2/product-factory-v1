# Orchestration
> **Directory purpose:** Factory-level orchestration contract. The AI-PDLC parent factory should apply this same six-mode contract to every sub-factory. This Product Factory declares and implements all six modes.

Modes: `FORWARD`, `BACKWARD`, `PARALLEL`, `CONDITIONAL`, `REWORK`, `ESCALATION`.

The parent AI-PDLC factory remains responsible for cross-factory orchestration. This package exposes compatible transitions/events so it can participate without bespoke logic.
