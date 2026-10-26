# Flipkart Voice360 — Complete Working Prototype

## Run
1. Install Python 3.
2. Extract this ZIP.
3. Open a terminal in the extracted folder.
4. Run:
   `python server.py`
5. Open:
   `http://127.0.0.1:8000`

No third-party Python packages are required.

## Included
- Executive Dashboard
- New Review trigger
- Active Cases
- Agent Activity
- Human Verification
- Human Approval
- Audit Trail
- KPI counts
- SQLite persistent case memory
- Simulated business tickets
- Re-planning after rejected actions
- Critical-case guardrail
- 17 academic test cases

## Demo inputs
Normal/mixed:
`The product is good but delivery was late and the package arrived damaged.`

Sarcasm:
`Amazing service. Only took them ten days to deliver.`

Critical:
`The phone is overheating and smells like burning while charging.`

Multi-department:
`The phone stopped working, delivery was late and customer support never responded.`

## Academic disclosure
This is an academic prototype using simulated/public-style reviews. It is not connected to Flipkart internal systems.
The NLP layer is transparent rule-based logic. The agentic layer is the orchestrated case process with state/memory,
decision gateways, human oversight, exceptions, re-planning, action tools and audit logs.
