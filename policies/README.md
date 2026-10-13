# AI-PDLC Security & Secure-Development Policies
> **Purpose:** Platform-level mandatory policy baseline consumed by every AI-PDLC factory.

These policies operationalize selected practices from NIST, CISA and OWASP for this AI-PDLC platform. They are an internal control baseline, not a claim of certification or complete compliance with any external framework.

## Baselines
- NIST SP 800-218 SSDF v1.1 (final) and SP 800-218A for GenAI/dual-use foundation-model secure development.
- NIST SP 800-207 Zero Trust Architecture and SP 800-207A cloud-native access-control guidance.
- CISA Secure by Design principles.
- CISA software supply-chain/SBOM guidance.
- OWASP Top 10:2025.
- OWASP API Security Top 10.
- OWASP Top 10 for LLM/GenAI (track current official release).
- OWASP ASVS 5.0.x.

## Enforcement model
Policies use MUST / SHOULD / MAY. `MUST` controls require evidence or an approved exception. Gates may block progression for missing mandatory evidence. Exceptions are time-bound, risk-owned and auditable.

See `policy-registry.yaml`, `control-crosswalk.yaml`, `security-gates.yaml`, and `exception-policy.yaml`.
