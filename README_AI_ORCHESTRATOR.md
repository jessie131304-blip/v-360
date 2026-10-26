# Flipkart Voice360 — AI Orchestrator Edition

This build adds a real LLM Orchestrator to the existing academic prototype.

## AI Orchestrator actions
- ROUTE_AND_ACT
- REQUEST_VERIFICATION
- REQUEST_APPROVAL
- ESCALATE

## Architecture
Rule-based NLP → LLM Orchestrator → deterministic safety guardrails → business tools → human oversight → audit trail.

## API
Uses the OpenAI Responses API when `OPENAI_API_KEY` is configured.

If no key/API is available, the prototype remains runnable in safe deterministic fallback mode.
