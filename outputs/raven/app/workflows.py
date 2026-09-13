import asyncio
import json
import uuid
from datetime import datetime, timezone
from .db import db


TEMPLATES = {
    "research": [
        ("Research current evidence", "web_research", False),
        ("Synthesize findings and recommendations", "openai_chat", False),
        ("Save durable conclusions", "semantic_memory", False),
    ],
    "social_campaign": [
        ("Research current trends and audience signals", "web_research", False),
        ("Design three differentiated account concepts", "content_text", False),
        ("Create content calendar and versioned media briefs", "content_text", False),
        ("Publish approved campaign through a connected account", "social", True),
        ("Measure results and adapt strategy", "social", True),
    ],
    "career_search": [
        ("Discover current roles from approved sources", "web_research", False),
        ("Score role fit against the canonical candidate profile", "career", False),
        ("Generate a versioned tailored resume and cover letter", "career", False),
        ("Review application target, answers, and documents", "career_apply", True),
        ("Submit and capture verification evidence", "career_apply", True),
    ],
    "market_research": [
        ("Research company, market, and recent evidence", "web_research", False),
        ("Build thesis, counter-thesis, and risk scenarios", "openai_chat", False),
        ("Prepare supervised paper-trade proposal", "brokerage", True),
    ],
    "general": [
        ("Analyze objective and gather context", "openai_chat", False),
        ("Prepare execution plan", "openai_chat", False),
        ("Execute through configured tools", "hermes", True),
        ("Verify outcome and report", "openai_chat", False),
    ],
}

# These capabilities can affect external systems. A connected registry row is
# not sufficient proof that this workflow has a typed, idempotent executor.
# Until one is wired here, fail closed instead of asking a model to simulate it.
EXTERNAL_ACTION_TOOLS={"social","career_apply","brokerage","hermes"}


def json_object(value):
    """Read records written before and after JSONB codec normalization."""
    for _ in range(2):
        if isinstance(value,str):
            try: value=json.loads(value)
            except json.JSONDecodeError: return {}
    return value if isinstance(value,dict) else {}


async def create_run(user_id: uuid.UUID, title: str, objective: str, template: str, department: str, autonomy: int, budget: float):
    template = template if template in TEMPLATES else "general"
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            run_id = await conn.fetchval("INSERT INTO runs(user_id,title,objective,template,department,autonomy,budget_usd) VALUES($1,$2,$3,$4,$5,$6,$7) RETURNING id",user_id,title,objective,template,department,autonomy,budget)
            for i,(step,tool,approval) in enumerate(TEMPLATES[template],1):
                await conn.execute("INSERT INTO run_steps(run_id,ordinal,title,tool,approval_required,input) VALUES($1,$2,$3,$4,$5,$6)",run_id,i,step,tool,approval,json.dumps({"objective":objective}))
            await conn.execute("INSERT INTO run_events(run_id,event,detail) VALUES($1,'run.created',$2)",run_id,json.dumps({"template":template,"autonomy":autonomy,"budget":budget}))
    return run_id


async def workflow_worker(ai, stop: asyncio.Event):
    while not stop.is_set():
        try:
            run = await claim_run()
            if run:
                await advance_run(ai,run)
            else:
                await asyncio.wait_for(stop.wait(),timeout=1.5)
        except asyncio.TimeoutError:
            pass
        except Exception as exc:
            # A worker fault is observable and retried; it never becomes fake success.
            await asyncio.sleep(2)


async def claim_run():
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            row=await conn.fetchrow("SELECT * FROM runs WHERE status IN ('queued','running') ORDER BY updated_at FOR UPDATE SKIP LOCKED LIMIT 1")
            if row and row["status"]=="queued":
                await conn.execute("UPDATE runs SET status='running',started_at=coalesce(started_at,now()),updated_at=now() WHERE id=$1",row["id"])
                await conn.execute("INSERT INTO run_events(run_id,event) VALUES($1,'run.started')",row["id"])
            return row


async def advance_run(ai,run):
    run_id=run["id"]
    step=await db.pool.fetchrow("SELECT * FROM run_steps WHERE run_id=$1 AND status IN ('pending','running') ORDER BY ordinal LIMIT 1",run_id)
    if not step:
        parts=await db.pool.fetch("SELECT output FROM run_steps WHERE run_id=$1 AND output != '{}' ORDER BY ordinal",run_id)
        result="\n\n".join(json_object(p["output"]).get("summary","") for p in parts)
        await db.pool.execute("UPDATE runs SET status='completed',result=$2,finished_at=now(),updated_at=now() WHERE id=$1",run_id,result[:30000])
        await db.pool.execute("INSERT INTO run_events(run_id,event) VALUES($1,'run.completed')",run_id)
        await db.pool.execute("INSERT INTO notifications(user_id,title,body,severity) SELECT user_id,$2,$3,'success' FROM runs WHERE id=$1",run_id,f"Mission complete: {run['title']}","RAVEN finished the mission. Open Mission Control for the full record.")
        return
    tool=await db.pool.fetchrow("SELECT * FROM tools WHERE id=$1",step["tool"])
    if not tool or tool["status"] not in ('ready','connected'):
        await db.pool.execute("UPDATE run_steps SET status='blocked',error=$2,finished_at=now() WHERE id=$1",step["id"],f"{step['tool']} is not connected")
        await db.pool.execute("UPDATE runs SET status='blocked',error=$2,updated_at=now() WHERE id=$1",run_id,f"{step['tool']} is not connected. No action was simulated.")
        await db.pool.execute("INSERT INTO run_events(run_id,event,detail) VALUES($1,'run.blocked',$2)",run_id,json.dumps({"tool":step["tool"],"reason":"not connected"}))
        return
    if step["approval_required"]:
        approval=await db.pool.fetchrow("SELECT * FROM approvals WHERE payload->>'run_id'=$1 AND payload->>'step_id'=$2 ORDER BY created_at DESC LIMIT 1",str(run_id),str(step["id"]))
        if not approval:
            aid=await db.pool.fetchval("INSERT INTO approvals(user_id,action,reason,target,data_summary,reversible,payload,expires_at) VALUES($1,$2,$3,$4,$5,false,$6,now()+interval '24 hours') RETURNING id",run["user_id"],step["title"],f"Mission {run['title']} reached a consequential step",tool["name"] if tool else step["tool"],f"Objective: {run['objective']}",json.dumps({"run_id":str(run_id),"step_id":str(step["id"])}))
            await db.pool.execute("UPDATE runs SET status='waiting_approval',updated_at=now() WHERE id=$1",run_id)
            await db.pool.execute("UPDATE run_steps SET status='waiting_approval' WHERE id=$1",step["id"])
            await db.pool.execute("INSERT INTO run_events(run_id,event,detail) VALUES($1,'approval.requested',$2)",run_id,json.dumps({"approval_id":str(aid),"step":step["title"]}))
            return
        if approval["status"]=="pending": return
        if approval["status"]=="rejected":
            await db.pool.execute("UPDATE run_steps SET status='cancelled',finished_at=now(),error='User rejected action' WHERE id=$1",step["id"])
            await db.pool.execute("UPDATE runs SET status='cancelled',finished_at=now(),updated_at=now() WHERE id=$1",run_id)
            return
    if step["tool"] in EXTERNAL_ACTION_TOOLS:
        reason=f"{step['tool']} has no typed, idempotent workflow executor installed. No external action was simulated."
        await db.pool.execute("UPDATE run_steps SET status='blocked',error=$2,finished_at=now() WHERE id=$1",step["id"],reason)
        await db.pool.execute("UPDATE runs SET status='blocked',error=$2,updated_at=now() WHERE id=$1",run_id,reason)
        await db.pool.execute("INSERT INTO run_events(run_id,event,detail) VALUES($1,'run.blocked',$2)",run_id,json.dumps({"tool":step["tool"],"reason":"typed executor missing","fail_closed":True}))
        return
    await db.pool.execute("UPDATE run_steps SET status='running',started_at=coalesce(started_at,now()) WHERE id=$1",step["id"])
    await db.pool.execute("INSERT INTO run_events(run_id,event,detail) VALUES($1,'step.started',$2)",run_id,json.dumps({"ordinal":step["ordinal"],"title":step["title"],"tool":step["tool"]}))
    prior=await db.pool.fetch("SELECT title,output FROM run_steps WHERE run_id=$1 AND ordinal<$2 ORDER BY ordinal",run_id,step["ordinal"])
    context="\n\n".join(f"{p['title']}: {json_object(p['output']).get('summary','')}" for p in prior)
    try:
        if step["tool"]=="web_research": result=await ai.research(run["objective"])
        else: result=await ai.chat([{"role":"user","content":f"Mission objective: {run['objective']}\nCurrent step: {step['title']}\nPrior work:\n{context}\nProduce a concrete, concise deliverable for this step."}],"")
        new_spent=float(run["spent_usd"])+result.cost
        if new_spent>float(run["budget_usd"]): raise RuntimeError("Mission budget exceeded")
        await db.pool.execute("UPDATE run_steps SET status='completed',output=$2,finished_at=now() WHERE id=$1",step["id"],json.dumps({"summary":result.text,"tokens":result.tokens_in+result.tokens_out,"cost":result.cost}))
        await db.pool.execute("UPDATE runs SET status='running',spent_usd=$2,updated_at=now() WHERE id=$1",run_id,new_spent)
        await db.pool.execute("INSERT INTO run_events(run_id,event,detail) VALUES($1,'step.completed',$2)",run_id,json.dumps({"ordinal":step["ordinal"],"cost":result.cost}))
    except Exception as exc:
        await db.pool.execute("UPDATE run_steps SET status='failed',error=$2,finished_at=now() WHERE id=$1",step["id"],str(exc)[:1000])
        await db.pool.execute("UPDATE runs SET status='failed',error=$2,finished_at=now(),updated_at=now() WHERE id=$1",run_id,str(exc)[:1000])
        await db.pool.execute("INSERT INTO run_events(run_id,event,detail) VALUES($1,'run.failed',$2)",run_id,json.dumps({"error":str(exc)[:500]}))
