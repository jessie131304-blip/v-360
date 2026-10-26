# Flipkart Voice360 — Gemini Orchestrator Edition

This build adds a real Gemini-powered LLM Orchestrator to the academic prototype.

Allowed AI decisions:
- ROUTE_AND_ACT
- REQUEST_VERIFICATION
- REQUEST_APPROVAL
- ESCALATE

Hybrid architecture:
Rule-based NLP → Gemini LLM Orchestrator → deterministic safety guardrails → tools → human oversight → audit trail.

API:
Uses the Gemini Interactions API through `GEMINI_API_KEY`.

Default model:
`gemini-3.7-flash`

If the Gemini API is unavailable, the prototype continues in safe deterministic fallback mode.
