# Flipkart Voice360 — Gemini Free-Tier AI Orchestrator Setup

## Architecture
Review
→ Intake & Context Agent
→ Rule-based NLP / Customer Intelligence
→ Gemini AI Orchestrator
→ deterministic safety guardrails
→ routing/action tools
→ human verification/approval
→ audit
→ closure

## Default model
`gemini-3.7-flash`

## Create a Gemini API key
1. Open Google AI Studio.
2. Go to API Keys.
3. Click Create API key.
4. Copy the key.
5. Never put the key in GitHub or client-side JavaScript.

## Add the key to Render
Render → v-360 → Environment

Add:
Key: `GEMINI_API_KEY`
Value: paste the Gemini API key

Optional:
Key: `GEMINI_MODEL`
Value: `gemini-3.7-flash`

Then click **Save, rebuild and deploy**.

## Verify
After deployment:
1. Submit a NEW review.
2. Open Case Details.
3. Confirm:
   - AI Orchestrator Mode = AI
   - AI Next Action is populated
   - AI Decision Reason is populated
   - AI Model = gemini-3.7-flash
4. Open Agent Activity and look for:
   `AI Orchestrator / Supervisor — SELECT_NEXT_ACTION`

## Free-tier fallback
If Gemini is unavailable, quota is exceeded, the key is invalid, or the project is not eligible for free tier, the app continues in:
`FALLBACK_DETERMINISTIC`

## Hard guardrails
Gemini cannot bypass:
- Confidence below 70% → Human Verification
- Safety/Hazard → Critical + Human Approval
- Critical cases cannot auto-close
- No real refunds, penalties, price changes, or customer messages
