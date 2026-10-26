# Voice360 — AI Orchestrator Setup on Render

## What changed
This version adds a real LLM-powered AI Orchestrator.

The flow is now:

Review
→ Intake & Context Agent
→ Customer Intelligence / NLP Agent
→ AI Orchestrator observes case state
→ AI selects one allowed next action
→ Triage / Routing tool
→ Human approval if needed
→ Resolution / Ticket tool
→ Audit / Closure

## Mandatory guardrails
The model cannot bypass these:
- Confidence below 70% → Human Verification
- Safety/Hazard → Critical + Human Approval
- Critical cases cannot auto-close
- No real refunds, price changes, seller penalties, or customer messages

## Add the API key in Render
Do NOT put the key in GitHub.

1. Open your Render service `v-360`.
2. Open **Environment**.
3. Add:
   - Key: `OPENAI_API_KEY`
   - Value: your OpenAI API key
4. Optional:
   - Key: `OPENAI_MODEL`
   - Value: `gpt-6-luna`
5. Save changes.
6. Render will redeploy.

## Why gpt-6-luna?
It is sufficient for a small structured orchestration decision and is a cost-efficient current model. You can change the model through `OPENAI_MODEL` without editing code.

## If the API is unavailable
The prototype does NOT break.
It logs:
`FALLBACK_DETERMINISTIC`

and continues using the validated routing/approval rules.

## How to prove the AI Agent during viva
Open:
- Case Details
- Agent Activity

Show:
- AI Orchestrator Mode = AI
- AI Next Action
- AI Decision Reason
- AI Model
- audit event: `AI Orchestrator / Supervisor — SELECT_NEXT_ACTION`

Then explain:
"The LLM observes the current case state and selects one permitted workflow action. Hard safety and confidence guardrails remain deterministic and can override the model."
