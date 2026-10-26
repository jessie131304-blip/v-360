
import sqlite3, json, uuid, os, urllib.request, urllib.error
from datetime import datetime, timezone

BASE = os.path.dirname(__file__)
DB = os.path.join(BASE, "voice360.db")

POSITIVE = ['good','great','excellent','amazing','perfect','love','loved','fast','worth','satisfied','happy','nice','best','smooth','useful','awesome']
NEGATIVE = ['bad','poor','terrible','awful','late','delayed','damaged','broken','defective','not working','stopped working','ignored','unresolved','overpriced','expensive','missing','leaking','failed','worst','slow']

ISSUE_RULES = {
    'Safety / Hazard':['overheating','overheated','burning','burning smell','fire','smoke','electric shock','shock','exploded','explosion'],
    'Product Quality':['defective','broken','stopped working','not working','poor quality','damaged product','faulty','dead'],
    'Delivery':['late','delayed','courier','not delivered','missing parcel','tracking','delivery'],
    'Packaging':['damaged box','torn box','crushed','seal broken','open package','poor packaging','leaking','package arrived damaged','box was damaged','packaging'],
    'Price':['expensive','overpriced','not worth','value for money','price'],
    'Customer Service':['support','refund','ignored','unresolved','no response','customer service','agent'],
    'Product Features':['battery','camera','display','design','storage','performance','feature','colour','color','size'],
    'Ordering Experience':['payment failed','cancellation','checkout','wrong order','payment','cancelled']
}

OWNERS = {
    'Safety / Hazard':'Product / Seller Management + Management',
    'Product Quality':'Product / Seller Management',
    'Delivery':'Logistics',
    'Packaging':'Operations',
    'Price':'Marketing / Pricing',
    'Customer Service':'Customer Support',
    'Product Features':'Product Management',
    'Ordering Experience':'E-commerce Operations'
}

ACTIONS = {
    'Safety / Hazard':'Immediately escalate the safety complaint for human review; block automatic closure.',
    'Product Quality':'Review seller/product quality and recurring defect pattern.',
    'Delivery':'Investigate delivery delay and logistics-partner performance.',
    'Packaging':'Review protective packaging and handling.',
    'Price':'Review price/value perception and competitor positioning.',
    'Customer Service':'Review response and resolution SLA.',
    'Product Features':'Capture feature feedback and assess product communication or roadmap need.',
    'Ordering Experience':'Review checkout, payment, cancellation or order-friction issue.'
}

def now():
    return datetime.now(timezone.utc).isoformat()

def db():
    c = sqlite3.connect(DB)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c=db()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS cases(
      case_id TEXT PRIMARY KEY, created_at TEXT, updated_at TEXT, review_text TEXT, source TEXT, rating TEXT,
      sentiment TEXT, confidence REAL, issues TEXT, severity TEXT, primary_department TEXT,
      secondary_departments TEXT, recommended_action TEXT, current_stage TEXT, human_approval TEXT,
      human_decision TEXT, exception_type TEXT, replan_count INTEGER, status TEXT, final_outcome TEXT
    );
    CREATE TABLE IF NOT EXISTS audit(
      id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, case_id TEXT, agent TEXT, action TEXT,
      decision TEXT, tool_used TEXT, stage TEXT
    );
    CREATE TABLE IF NOT EXISTS tickets(
      ticket_id TEXT PRIMARY KEY, case_id TEXT, owner TEXT, secondary_owners TEXT, priority TEXT,
      action TEXT, created_at TEXT, status TEXT
    );
    """)
    # Lightweight schema migration for AI Orchestrator evidence.
    existing = {r[1] for r in c.execute("PRAGMA table_info(cases)").fetchall()}
    for col, ddl in [
        ("ai_orchestrator_mode", "TEXT"),
        ("ai_next_action", "TEXT"),
        ("ai_reason", "TEXT"),
        ("ai_model", "TEXT")
    ]:
        if col not in existing:
            c.execute(f"ALTER TABLE cases ADD COLUMN {col} {ddl}")
    c.commit(); c.close()

def log(case_id,agent,action,decision,tool,stage):
    c=db(); c.execute("INSERT INTO audit(timestamp,case_id,agent,action,decision,tool_used,stage) VALUES(?,?,?,?,?,?,?)",
                      (now(),case_id,agent,action,decision,tool,stage)); c.commit(); c.close()

def save(d):
    c=db()
    fields = [
        "case_id","created_at","updated_at","review_text","source","rating",
        "sentiment","confidence","issues","severity","primary_department",
        "secondary_departments","recommended_action","current_stage",
        "human_approval","human_decision","exception_type","replan_count",
        "status","final_outcome","ai_orchestrator_mode","ai_next_action",
        "ai_reason","ai_model"
    ]
    vals = [
        d.get("case_id"),d.get("created_at"),d.get("updated_at"),d.get("review_text"),
        d.get("source"),d.get("rating"),d.get("sentiment"),d.get("confidence"),
        json.dumps(d.get("issues",[])),d.get("severity"),d.get("primary_department"),
        json.dumps(d.get("secondary_departments",[])),d.get("recommended_action"),
        d.get("current_stage"),d.get("human_approval"),d.get("human_decision"),
        d.get("exception_type"),d.get("replan_count",0),d.get("status"),
        d.get("final_outcome"),d.get("ai_orchestrator_mode"),d.get("ai_next_action"),
        d.get("ai_reason"),d.get("ai_model")
    ]
    placeholders=",".join(["?"]*len(fields))
    updates=",".join([f"{f}=excluded.{f}" for f in fields if f!="case_id"])
    c.execute(
        f"INSERT INTO cases({','.join(fields)}) VALUES({placeholders}) "
        f"ON CONFLICT(case_id) DO UPDATE SET {updates}",
        vals
    )
    c.commit(); c.close()

def row_to_case(r):
    if not r: return None
    d=dict(r); d["issues"]=json.loads(d["issues"] or "[]"); d["secondary_departments"]=json.loads(d["secondary_departments"] or "[]")
    d["audit_log"]=get_audit(d["case_id"])
    return d

def get_case(cid):
    c=db(); r=c.execute("SELECT * FROM cases WHERE case_id=?",(cid,)).fetchone(); c.close(); return row_to_case(r)

def get_cases():
    c=db(); rs=c.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall(); c.close(); return [row_to_case(r) for r in rs]

def get_audit(cid=None):
    c=db()
    if cid: rs=c.execute("SELECT timestamp,case_id,agent,action,decision,tool_used,stage FROM audit WHERE case_id=? ORDER BY id",(cid,)).fetchall()
    else: rs=c.execute("SELECT timestamp,case_id,agent,action,decision,tool_used,stage FROM audit ORDER BY id DESC").fetchall()
    c.close(); return [dict(r) for r in rs]

def get_tickets():
    c=db(); rs=c.execute("SELECT * FROM tickets ORDER BY created_at DESC").fetchall(); c.close()
    out=[]
    for r in rs:
        d=dict(r); d["secondary_owners"]=json.loads(d["secondary_owners"] or "[]"); out.append(d)
    return out


def ai_orchestrator_available():
    return bool(os.environ.get("OPENAI_API_KEY","").strip())

def candidate_context(d):
    """Deterministic business context supplied to the AI, while preserving hard guardrails."""
    text=d["review_text"].lower()
    issues=d.get("issues",[])
    safety="Safety / Hazard" in issues
    severe=any(x in text for x in ['stopped working','not working','defective','broken'])
    if safety: severity="Critical"
    elif severe or len(issues)>=3: severity="High"
    elif d.get("sentiment") in ["Negative","Mixed"] or any(i in issues for i in ['Delivery','Packaging','Customer Service','Ordering Experience','Price']): severity="Medium"
    else: severity="Low"
    departments=[]
    for i in issues:
        o=OWNERS.get(i)
        if o and o not in departments:
            departments.append(o)
    return {
        "severity_candidate": severity,
        "primary_department_candidate": departments[0] if departments else "Customer Experience",
        "secondary_departments_candidate": departments[1:],
        "department_count": len(departments)
    }

def extract_response_text(resp):
    # Responses API returns output -> message -> content -> output_text.
    chunks=[]
    for item in resp.get("output",[]):
        if item.get("type")=="message":
            for c in item.get("content",[]):
                if c.get("type")=="output_text" and c.get("text"):
                    chunks.append(c["text"])
    return "\n".join(chunks).strip()

def ai_orchestrator_decision(d):
    """
    Real LLM Orchestrator.
    Chooses the next allowed action using case state.
    Hard safety/verification rules are enforced after the model returns.
    """
    ctx=candidate_context(d)

    # Mandatory guardrails override any model choice.
    if d.get("confidence") is not None and d["confidence"] < 70:
        return {
            "mode":"GUARDRAIL",
            "next_action":"REQUEST_VERIFICATION",
            "primary_department":ctx["primary_department_candidate"],
            "secondary_departments":ctx["secondary_departments_candidate"],
            "requires_human":True,
            "reason":"Confidence is below the mandatory 70% threshold; human verification is required.",
            "model":"hard_guardrail"
        }
    if "Safety / Hazard" in d.get("issues",[]):
        return {
            "mode":"GUARDRAIL",
            "next_action":"REQUEST_APPROVAL",
            "primary_department":"Product / Seller Management + Management",
            "secondary_departments":ctx["secondary_departments_candidate"],
            "requires_human":True,
            "reason":"Safety/hazard signal detected. Critical cases must escalate and cannot auto-close.",
            "model":"hard_guardrail"
        }

    key=os.environ.get("OPENAI_API_KEY","").strip()
    model=os.environ.get("OPENAI_MODEL","gpt-6-luna").strip() or "gpt-6-luna"

    if not key:
        # Deterministic fallback lets classroom demo continue without secrets/API access.
        if ctx["severity_candidate"] in ["High","Critical"] or ctx["department_count"]>=3:
            action="REQUEST_APPROVAL"
            human=True
        else:
            action="ROUTE_AND_ACT"
            human=False
        return {
            "mode":"FALLBACK_DETERMINISTIC",
            "next_action":action,
            "primary_department":ctx["primary_department_candidate"],
            "secondary_departments":ctx["secondary_departments_candidate"],
            "requires_human":human,
            "reason":"OpenAI API key is not configured; existing verified business rules selected the next action.",
            "model":"none"
        }

    allowed=["ROUTE_AND_ACT","REQUEST_VERIFICATION","REQUEST_APPROVAL","ESCALATE"]
    prompt = {
        "goal":"Safely progress this customer-feedback case toward a resolved and auditable outcome.",
        "constraints":[
            "Choose exactly one next_action from the allowed_actions.",
            "Do not issue refunds, penalties, price changes, seller sanctions, or customer messages.",
            "Prefer human oversight when business risk is consequential or evidence is ambiguous.",
            "Use the provided case state and candidate business context.",
            "Return JSON only. Do not include markdown."
        ],
        "allowed_actions":allowed,
        "case_state":{
            "case_id":d.get("case_id"),
            "review_text":d.get("review_text"),
            "sentiment":d.get("sentiment"),
            "confidence":d.get("confidence"),
            "issues":d.get("issues",[]),
            "current_stage":d.get("current_stage"),
            "replan_count":d.get("replan_count",0),
            "previous_human_decision":d.get("human_decision"),
            **ctx
        },
        "required_json":{
            "next_action":"one allowed action",
            "primary_department":"string",
            "secondary_departments":["string"],
            "requires_human":"boolean",
            "reason":"one concise managerial rationale"
        }
    }

    body=json.dumps({
        "model":model,
        "input":[
            {
                "role":"system",
                "content":"You are the Voice360 AI Orchestrator. Select the next business-process action from the allowed set. Return only valid JSON."
            },
            {
                "role":"user",
                "content":json.dumps(prompt)
            }
        ],
        "max_output_tokens":300
    }).encode("utf-8")

    req=urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=body,
        method="POST",
        headers={
            "Authorization":f"Bearer {key}",
            "Content-Type":"application/json"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp=json.loads(r.read().decode("utf-8"))
        raw=extract_response_text(resp)
        # tolerate accidental code fences while still requiring a JSON object
        raw=raw.strip()
        if raw.startswith("```"):
            raw=raw.replace("```json","").replace("```","").strip()
        decision=json.loads(raw)
        action=decision.get("next_action")
        if action not in allowed:
            raise ValueError("AI returned unsupported next_action")
        return {
            "mode":"AI",
            "next_action":action,
            "primary_department":decision.get("primary_department") or ctx["primary_department_candidate"],
            "secondary_departments":decision.get("secondary_departments") if isinstance(decision.get("secondary_departments"),list) else ctx["secondary_departments_candidate"],
            "requires_human":bool(decision.get("requires_human")),
            "reason":str(decision.get("reason") or "AI selected the next workflow action."),
            "model":model
        }
    except Exception as e:
        if ctx["severity_candidate"] in ["High","Critical"] or ctx["department_count"]>=3:
            action="REQUEST_APPROVAL"; human=True
        else:
            action="ROUTE_AND_ACT"; human=False
        return {
            "mode":"FALLBACK_DETERMINISTIC",
            "next_action":action,
            "primary_department":ctx["primary_department_candidate"],
            "secondary_departments":ctx["secondary_departments_candidate"],
            "requires_human":human,
            "reason":f"AI call unavailable; safe deterministic fallback used ({type(e).__name__}).",
            "model":model
        }

def run_orchestrator(d):
    decision=ai_orchestrator_decision(d)
    d["ai_orchestrator_mode"]=decision["mode"]
    d["ai_next_action"]=decision["next_action"]
    d["ai_reason"]=decision["reason"]
    d["ai_model"]=decision["model"]
    d["updated_at"]=now()
    save(d)
    log(
        d["case_id"],
        "AI Orchestrator / Supervisor",
        "SELECT_NEXT_ACTION",
        f"{decision['next_action']} | {decision['reason']}",
        f"OpenAI Responses API ({decision['model']})" if decision["mode"]=="AI" else decision["mode"],
        "ORCHESTRATION"
    )

    if decision["next_action"]=="REQUEST_VERIFICATION":
        d.update(status="PENDING_VERIFICATION",current_stage="HUMAN_VERIFICATION",human_approval="REQUIRED",final_outcome="Paused for human verification.",updated_at=now())
        save(d)
        log(d["case_id"],"Orchestrator / Supervisor","PAUSE_FOR_VERIFICATION",decision["reason"],"AI decision + guardrails","HUMAN_VERIFICATION")
        return get_case(d["case_id"])

    # Triage remains a transparent business tool. We pass AI routing hints into the case.
    d["_ai_primary"]=decision.get("primary_department")
    d["_ai_secondary"]=decision.get("secondary_departments",[])
    d["_ai_requires_human"]=decision.get("requires_human",False)
    d["_ai_action"]=decision["next_action"]
    return triage(d)

def create_case(review_text,source="Web Form",rating=None):
    cid="FV360-"+datetime.now().strftime("%H%M%S")+"-"+uuid.uuid4().hex[:5].upper()
    d={"case_id":cid,"created_at":now(),"updated_at":now(),"review_text":review_text.strip(),"source":source,"rating":rating,
       "sentiment":None,"confidence":None,"issues":[],"severity":None,"primary_department":None,"secondary_departments":[],
       "recommended_action":None,"current_stage":"INTAKE","human_approval":None,"human_decision":None,
       "exception_type":"","replan_count":0,"status":"OPEN","final_outcome":""}
    save(d); log(cid,"Intake & Context Agent","CASE_CREATED","Valid review received" if d["review_text"] else "Blank review received","Web form / Case DB","INTAKE")
    if not d["review_text"]:
        d.update(current_stage="INVALID_INPUT",status="ESCALATED",exception_type="INVALID_INPUT",final_outcome="Valid review text required before analysis.",updated_at=now())
        save(d); log(cid,"Orchestrator / Supervisor","EXCEPTION_DETECTED","Blank input; fail safely","Validation rule","INVALID_INPUT"); return get_case(cid)
    return intelligence(d)

def intelligence(d):
    text=d["review_text"].lower(); hits=lambda arr:[x for x in arr if x in text]
    ph,nh=hits(POSITIVE),hits(NEGATIVE); issues=[]
    for k,v in ISSUE_RULES.items():
        if hits(v): issues.append(k)
    sarcasm=(any(x in text for x in ['amazing','great','fantastic','perfect']) and any(x in text for x in ['late','delayed','days to deliver','worst','broken']))
    sentiment="Mixed" if ph and nh else "Negative" if nh else "Positive" if ph else "Neutral"
    confidence=84; exception=""
    if sarcasm: confidence=55; exception="SARCASM_OR_CONTRADICTION"
    elif sentiment=="Mixed": confidence=78
    elif not issues and not ph and not nh: confidence=58; exception="LOW_CONFIDENCE"
    elif len(text)<12: confidence=60; exception="LOW_CONFIDENCE"
    d.update(sentiment=sentiment,confidence=confidence,issues=issues,exception_type=exception,current_stage="CONFIDENCE_CHECK",updated_at=now())
    save(d); log(d["case_id"],"Customer Intelligence Agent","NLP_ANALYSIS",f"Sentiment={sentiment}; Issues={', '.join(issues) or 'None'}; Confidence={confidence}","Rule-based NLP","ANALYZE")
    return run_orchestrator(d)

def triage(d):
    text=d["review_text"].lower(); issues=d["issues"]
    safety="Safety / Hazard" in issues
    severe=any(x in text for x in ['stopped working','not working','defective','broken'])
    if safety: sev="Critical"
    elif severe or len(issues)>=3: sev="High"
    elif d["sentiment"] in ["Negative","Mixed"] or any(i in issues for i in ['Delivery','Packaging','Customer Service','Ordering Experience','Price']): sev="Medium"
    else: sev="Low"
    depts=[]
    for i in issues:
        o=OWNERS.get(i)
        if o and o not in depts: depts.append(o)
    primary=d.pop("_ai_primary",None) or (depts[0] if depts else "Customer Experience")
    ai_secondaries=d.pop("_ai_secondary",None)
    secondaries=ai_secondaries if isinstance(ai_secondaries,list) and ai_secondaries else depts[1:]
    ai_requires=bool(d.pop("_ai_requires_human",False))
    ai_action=d.pop("_ai_action",None)
    rec=" ".join(ACTIONS[i] for i in issues if i in ACTIONS) or "Monitor and record customer feedback."
    approval=sev in ["High","Critical"] or len(depts)>=3 or ai_requires or ai_action in ["REQUEST_APPROVAL","ESCALATE"]
    d.update(severity=sev,primary_department=primary,secondary_departments=secondaries,recommended_action=rec,current_stage="APPROVAL_CHECK",updated_at=now())
    save(d); log(d["case_id"],"Triage & Routing Agent","TRIAGE_AND_ROUTE",f"Severity={sev}; Primary={primary}; Approval={approval}; AI={d.get('ai_next_action')}","Routing + severity KB","TRIAGE")
    if approval:
        d.update(status="PENDING_APPROVAL",current_stage="HUMAN_APPROVAL",human_approval="REQUIRED",final_outcome="Paused for manager approval.",updated_at=now())
        save(d); log(d["case_id"],"Orchestrator / Supervisor","PAUSE_FOR_APPROVAL",f"Approval required for severity={sev} / departments={len(depts)}","Approval policy","HUMAN_APPROVAL")
        return get_case(d["case_id"])
    return resolve(d)

def resolve(d):
    d.update(current_stage="ACTION",updated_at=now()); save(d)
    tid="TKT-"+d["case_id"]
    c=db(); c.execute("INSERT OR REPLACE INTO tickets VALUES(?,?,?,?,?,?,?,?)",(tid,d["case_id"],d["primary_department"],json.dumps(d["secondary_departments"]),d["severity"],d["recommended_action"],now(),"CREATED")); c.commit(); c.close()
    log(d["case_id"],"Resolution / Action Agent","CREATE_TICKET",f"{tid} assigned to {d['primary_department']}","Simulated ticket tool","ACTION")
    if d["severity"]=="Critical":
        d.update(status="PENDING_APPROVAL",current_stage="HUMAN_APPROVAL",final_outcome="Critical case cannot auto-close; human closure confirmation required.",updated_at=now())
        save(d); log(d["case_id"],"Orchestrator / Supervisor","BLOCK_CRITICAL_AUTOCLOSE","Critical case requires human confirmation","Critical guardrail","HUMAN_APPROVAL")
    else:
        d.update(status="CLOSED",current_stage="CLOSED",final_outcome=f"Case closed with simulated action ticket {tid}.",updated_at=now())
        save(d); log(d["case_id"],"Orchestrator / Supervisor","CASE_CLOSED","Checks passed and ticket created","Case state + ticket","CLOSURE")
    return get_case(d["case_id"])

def human_decision(cid,decision,note="",corrected_sentiment=None,corrected_issues=None,modified_action=None):
    d=get_case(cid)
    if not d: raise KeyError("Case not found")
    decision=decision.upper(); d["human_decision"]=decision; d["updated_at"]=now()
    if decision in ["VERIFY","CORRECT"]:
        if decision=="CORRECT":
            if corrected_sentiment: d["sentiment"]=corrected_sentiment
            if corrected_issues is not None: d["issues"]=corrected_issues
        d.update(status="OPEN",current_stage="TRIAGE",human_approval="COMPLETED"); save(d)
        log(cid,"Human Reviewer","CORRECT_CLASSIFICATION" if decision=="CORRECT" else "VERIFY_CLASSIFICATION",note or "Human verification completed","Human verification control","HUMAN_VERIFICATION")
        log(cid,"Orchestrator / Supervisor","RESUME_AFTER_VERIFICATION","Resume at Triage using verified state","Case memory","TRIAGE")
        return triage(d)
    if decision in ["APPROVE","MODIFY"]:
        if decision=="MODIFY" and modified_action: d["recommended_action"]=modified_action
        d.update(human_approval="APPROVED" if decision=="APPROVE" else "MODIFIED",status="OPEN",current_stage="ACTION"); save(d)
        log(cid,"Human Manager","APPROVE_ACTION" if decision=="APPROVE" else "MODIFY_ACTION",modified_action or note or "Action approved","Human approval control","HUMAN_APPROVAL")
        return resolve(d)
    if decision=="REJECT":
        d["replan_count"]=int(d.get("replan_count") or 0)+1; d["human_approval"]="REJECTED"
        log(cid,"Human Manager","REJECT_ACTION",note or "Action rejected","Human approval control","HUMAN_APPROVAL")
        if d["replan_count"]>2:
            d.update(status="ESCALATED",current_stage="ESCALATED",final_outcome="Escalated after maximum re-plan attempts.",updated_at=now()); save(d)
            log(cid,"Orchestrator / Supervisor","MAX_REPLAN_ESCALATION","Maximum re-plan attempts exceeded","Re-plan policy","ESCALATION")
            return get_case(cid)
        if "Delivery" in d["issues"]: alt="Create a logistics investigation task, review courier delay evidence, and monitor repeat delivery complaints before closure."
        elif "Product Quality" in d["issues"]: alt="Create a seller/product quality review task and inspect recurrence before taking further action."
        else: alt="Create a manual CX review task and request department confirmation before closure."
        d.update(recommended_action=alt,status="PENDING_APPROVAL",current_stage="HUMAN_APPROVAL",updated_at=now()); save(d)
        log(cid,"Resolution / Action Agent","REPLAN_ACTION",alt,"Rule-based action library","REPLAN")
        log(cid,"Orchestrator / Supervisor","RETURN_FOR_APPROVAL",f"Alternative prepared; re-plan attempt {d['replan_count']} of 2","Approval policy","HUMAN_APPROVAL")
        return get_case(cid)
    raise ValueError("Use VERIFY, CORRECT, APPROVE, MODIFY or REJECT")

def seed_demo_cases():
    c = db()
    count = c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    c.close()
    if count > 0:
        return

    demo_reviews = [
        ("The product is excellent and arrived on time.", "Demo Seed", 5),
        ("Delivery was late but the product is good.", "Demo Seed", 3),
        ("The box was damaged and delivery was delayed.", "Demo Seed", 2),
        ("This product is overpriced and not worth the price.", "Demo Seed", 2),
        ("Customer support ignored me and there was no response.", "Demo Seed", 1),
        ("The camera and battery performance are excellent.", "Demo Seed", 5),
        ("Payment failed during checkout.", "Demo Seed", 1),
        ("Good product but the packaging was poor.", "Demo Seed", 3),
        ("The phone stopped working after two days.", "Demo Seed", 1),
        ("Delivery was late, package damaged, and support ignored me.", "Demo Seed", 1),
        ("The product is okay, nothing special.", "Demo Seed", 3),
        ("Nice design but expensive.", "Demo Seed", 3),
        ("Amazing service. Only took them ten days to deliver.", "Demo Seed", 1),
        ("The phone is overheating and smells like burning while charging.", "Demo Seed", 1),
        ("The phone stopped working, delivery was late and customer support never responded.", "Demo Seed", 1),
        ("Worst support. Refund unresolved and delivery delayed.", "Demo Seed", 1),
        ("Very good value for money and smooth performance.", "Demo Seed", 5),
        ("Package arrived damaged but delivery was fast.", "Demo Seed", 3),
        ("Checkout was smooth but the product feels expensive.", "Demo Seed", 3),
        ("The display is great, but customer support took too long to respond.", "Demo Seed", 3),
    ]

    created = []
    for review, source, rating in demo_reviews:
        created.append(create_case(review, source, rating))

    # Make one low-confidence case explicitly verified so the dashboard also shows a completed human loop.
    for d in created:
        if d.get("status") == "PENDING_VERIFICATION":
            try:
                human_decision(
                    d["case_id"],
                    "CORRECT",
                    "Demo reviewer corrected ambiguous/sarcastic classification.",
                    "Negative",
                    ["Delivery"] if "deliver" in d["review_text"].lower() else d.get("issues", [])
                )
                break
            except Exception:
                pass

    # Make one high case go through reject -> re-plan -> approve to show re-planning evidence.
    for d in created:
        current = get_case(d["case_id"])
        if current and current.get("status") == "PENDING_APPROVAL" and current.get("severity") == "High":
            try:
                human_decision(current["case_id"], "REJECT", "Initial action too generic for demo.")
                human_decision(current["case_id"], "APPROVE", "Re-planned action approved for demo.")
                break
            except Exception:
                pass

def kpis():
    c=db()
    total=c.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
    closed=c.execute("SELECT COUNT(*) FROM cases WHERE status='CLOSED'").fetchone()[0]
    pv=c.execute("SELECT COUNT(*) FROM cases WHERE status='PENDING_VERIFICATION'").fetchone()[0]
    pa=c.execute("SELECT COUNT(*) FROM cases WHERE status='PENDING_APPROVAL'").fetchone()[0]
    esc=c.execute("SELECT COUNT(*) FROM cases WHERE status='ESCALATED'").fetchone()[0]
    crit=c.execute("SELECT COUNT(*) FROM cases WHERE severity='Critical'").fetchone()[0]
    c.close()
    return {"total_cases":total,"closed":closed,"pending_verification":pv,"pending_approval":pa,"escalated":esc,"critical":crit,"audit_coverage_pct":100 if total else 0}
