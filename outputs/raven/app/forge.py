"""Durable, owner-scoped controller for RAVEN Forge engineering jobs."""
from __future__ import annotations

import asyncio
import hmac
import json
import re
import uuid
from pathlib import PurePosixPath

import httpx
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field

from .auth import current_user
from .db import db

router=APIRouter(prefix="/api/forge",tags=["forge"])
_settings=None

VALID_STATES={"queued","initializing","inspecting","planning","running","testing","verifying","waiting_for_approval","paused","blocked","completed","failed","cancelled","resuming"}
TERMINAL_STATES={"completed","failed","cancelled"}

def configure(settings):
    global _settings
    _settings=settings

async def bootstrap():
    uid=await db.pool.fetchval("SELECT id FROM users WHERE username='owner'")
    if uid:
        await db.pool.execute("INSERT INTO forge_projects(user_id,display_name,repo_path,default_branch,runtime_metadata) VALUES($1,'RAVEN','.', 'main',$2) ON CONFLICT(user_id,repo_path) DO NOTHING",uid,json.dumps({'source':'built_in','workspace_boundary':'configured Forge mount'}))

def record(row):
    if not row:return None
    out=dict(row)
    for key,value in list(out.items()):
        if isinstance(value,uuid.UUID):out[key]=str(value)
    return out

def safe_repo_path(value:str)->str:
    value=value.replace('\\','/').strip()
    if value.startswith('/') or re.match(r"^[A-Za-z]:/",value):
        raise HTTPException(400,"Project path must stay inside the configured Forge workspace root.")
    value=value.strip('/') or '.'
    path=PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or any(part in {'','.env','.git'} for part in path.parts if part!='.'):
        raise HTTPException(400,"Project path must stay inside the configured Forge workspace root.")
    if not re.fullmatch(r"[A-Za-z0-9._/ -]{1,500}",value):raise HTTPException(400,"Project path contains unsupported characters.")
    return value

async def hermes(path:str,payload:dict|None=None,timeout:float=30):
    if not _settings or not _settings.hermes_url or not _settings.hermes_token:raise HTTPException(503,"Hermes is not configured.")
    async with httpx.AsyncClient(timeout=timeout) as client:
        response=await client.request("POST" if payload is not None else "GET",_settings.hermes_url.rstrip('/')+path,headers={"Authorization":"Bearer "+_settings.hermes_token},json=payload)
    if not response.is_success:
        try:detail=response.json().get('detail')
        except Exception:detail=None
        raise HTTPException(502,str(detail or "Hermes rejected the Forge request."))
    return response.json()

class ProjectIn(BaseModel):
    display_name:str=Field(min_length=1,max_length=120)
    repo_path:str=Field(min_length=1,max_length=500)
    default_branch:str=Field("main",min_length=1,max_length=120)

class ExternalProjectIn(BaseModel):
    display_name:str=Field(min_length=1,max_length=120)
    template:str=Field("website",pattern="^(website|blank|python)$")
    default_branch:str=Field("main",pattern=r"^[A-Za-z0-9._/-]{1,120}$")

class ProjectOpenIn(BaseModel):action:str=Field(pattern="^(folder|vscode)$")

class JobIn(BaseModel):
    project_id:uuid.UUID
    request:str=Field(min_length=3,max_length=20000)
    title:str=Field("",max_length=160)
    execution_mode:str=Field("build",pattern="^(ask|plan|build|autonomous)$")
    provider_policy:str=Field("auto",pattern="^(auto|local|openrouter|nvidia|codex)$")
    model:str=Field("",max_length=200)
    max_iterations:int=Field(12,ge=1,le=40)
    max_runtime_seconds:int=Field(1800,ge=60,le=14400)

class MessageIn(BaseModel):content:str=Field(min_length=1,max_length=12000)
class ContinueIn(BaseModel):iterations:int=Field(8,ge=1,le=40)
class EventIn(BaseModel):
    job_id:uuid.UUID
    event_type:str=Field(min_length=1,max_length=80)
    stage:str=Field("",max_length=80)
    summary:str=Field(min_length=1,max_length=2000)
    metadata:dict=Field(default_factory=dict)

@router.get("/providers")
async def providers(request:Request):
    await current_user(request,request.cookies.get("raven_session"))
    return await hermes("/forge/providers")

@router.get("/projects")
async def projects(request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")))
    rows=await db.pool.fetch("SELECT * FROM forge_projects WHERE user_id=$1 ORDER BY updated_at DESC",uid)
    return [record(x) for x in rows]

@router.post("/projects")
async def add_project(data:ProjectIn,request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")));path=safe_repo_path(data.repo_path)
    inspected=await hermes("/forge/projects/inspect",{"repo_path":path})
    row=await db.pool.fetchrow("INSERT INTO forge_projects(user_id,display_name,repo_path,default_branch,runtime_metadata) VALUES($1,$2,$3,$4,$5) ON CONFLICT(user_id,repo_path) DO UPDATE SET display_name=excluded.display_name,default_branch=excluded.default_branch,runtime_metadata=excluded.runtime_metadata,updated_at=now() RETURNING *",uid,data.display_name,path,data.default_branch,json.dumps(inspected))
    return record(row)

@router.post("/projects/external")
async def create_external_project(data:ExternalProjectIn,request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")))
    slug=re.sub(r"[^a-z0-9]+","-",data.display_name.lower()).strip('-')[:80]
    if not slug:raise HTTPException(400,"Project name must contain letters or numbers.")
    created=await hermes("/forge/projects/create",{"slug":slug,"display_name":data.display_name,"template":data.template,"default_branch":data.default_branch})
    path=f"external/{slug}"
    row=await db.pool.fetchrow("INSERT INTO forge_projects(user_id,display_name,repo_path,default_branch,runtime_metadata) VALUES($1,$2,$3,$4,$5) ON CONFLICT(user_id,repo_path) DO UPDATE SET display_name=excluded.display_name,default_branch=excluded.default_branch,runtime_metadata=excluded.runtime_metadata,updated_at=now() RETURNING *",uid,data.display_name,path,data.default_branch,json.dumps({**created,'source':'external_projects_root'}))
    return record(row)

@router.post("/projects/{project_id}/open")
async def open_external_project(project_id:uuid.UUID,data:ProjectOpenIn,request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")))
    project=await db.pool.fetchrow("SELECT * FROM forge_projects WHERE id=$1 AND user_id=$2",project_id,uid)
    if not project:raise HTTPException(404,"Forge project not found.")
    path=str(project['repo_path'])
    if not path.startswith('external/') or not re.fullmatch(r"external/[a-z0-9][a-z0-9-]{0,79}",path):raise HTTPException(400,"Only external Forge projects can be opened from this control.")
    if not (_settings and _settings.desktop_bridge_enabled and _settings.desktop_bridge_token):raise HTTPException(503,"Connect the Windows desktop companion before opening project folders or VS Code.")
    async with httpx.AsyncClient(timeout=12) as client:
        response=await client.post(_settings.desktop_bridge_url.rstrip('/')+'/project',headers={"Authorization":"Bearer "+_settings.desktop_bridge_token},json={"slug":path.removeprefix('external/'),"action":data.action})
    try:result=response.json()
    except Exception:result={"ok":False,"error":"Desktop companion returned an invalid response."}
    if not response.is_success or not result.get('ok'):raise HTTPException(502,result.get('error') or "The desktop companion could not open the project.")
    return result

@router.get("/jobs")
async def jobs(request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")))
    rows=await db.pool.fetch("SELECT j.*,p.display_name project_name FROM forge_jobs j JOIN forge_projects p ON p.id=j.project_id WHERE j.user_id=$1 ORDER BY j.updated_at DESC LIMIT 100",uid)
    return [record(x) for x in rows]

@router.post("/jobs")
async def create_job(data:JobIn,request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")))
    project=await db.pool.fetchrow("SELECT * FROM forge_projects WHERE id=$1 AND user_id=$2",data.project_id,uid)
    if not project:raise HTTPException(404,"Forge project not found.")
    title=data.title.strip() or re.sub(r"\s+"," ",data.request)[:80]
    row=await db.pool.fetchrow("INSERT INTO forge_jobs(user_id,project_id,title,user_request,execution_mode,provider_policy,selected_model,max_iterations,max_runtime_seconds) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9) RETURNING *",uid,data.project_id,title,data.request,data.execution_mode,data.provider_policy,data.model,data.max_iterations,data.max_runtime_seconds)
    await db.pool.execute("INSERT INTO forge_messages(job_id,role,content) VALUES($1,'user',$2)",row['id'],data.request)
    await event(row['id'],'job_created','queued',f"Forge job created for {project['display_name']}.",{'mode':data.execution_mode,'provider_policy':data.provider_policy})
    return record(row)

def voice_command(message:str)->str|None:
    """Recognize explicit Forge delegation without stealing ordinary coding chat."""
    text=re.sub(r"\s+"," ",message).strip(" .!?")
    patterns=(r"(?:ask|tell) forge to (.+)",r"(?:have|make) forge (.+)",r"(?:start|run) (?:a )?forge (?:job|task)(?: to| for)? (.+)",r"forge[, :] +(build|fix|inspect|test|debug|implement|refactor|review) (.+)")
    for pattern in patterns:
        match=re.fullmatch(pattern,text,re.I)
        if match:return " ".join(match.groups()).strip()[:20000]
    return None

async def enqueue_default(user_id:uuid.UUID,task:str,mode:str="build"):
    project=await db.pool.fetchrow("SELECT * FROM forge_projects WHERE user_id=$1 ORDER BY (repo_path='.') DESC,updated_at DESC LIMIT 1",user_id)
    if not project:raise HTTPException(409,"Register a Forge project first.")
    title=re.sub(r"\s+"," ",task)[:80]
    row=await db.pool.fetchrow("INSERT INTO forge_jobs(user_id,project_id,title,user_request,execution_mode,provider_policy,max_iterations,max_runtime_seconds) VALUES($1,$2,$3,$4,$5,'auto',12,1800) RETURNING *",user_id,project['id'],title,task,mode)
    await db.pool.execute("INSERT INTO forge_messages(job_id,role,content) VALUES($1,'user',$2)",row['id'],task)
    await event(row['id'],'job_created','queued',f"Forge job created for {project['display_name']}.",{'mode':mode,'provider_policy':'auto','origin':'voice_or_text_router'})
    return record(row)

@router.get("/jobs/{job_id}")
async def job_detail(job_id:uuid.UUID,request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")))
    job=await db.pool.fetchrow("SELECT j.*,p.display_name project_name,p.repo_path,p.default_branch FROM forge_jobs j JOIN forge_projects p ON p.id=j.project_id WHERE j.id=$1 AND j.user_id=$2",job_id,uid)
    if not job:raise HTTPException(404,"Forge job not found.")
    events=await db.pool.fetch("SELECT * FROM forge_job_events WHERE job_id=$1 ORDER BY id DESC LIMIT 300",job_id)
    messages=await db.pool.fetch("SELECT * FROM forge_messages WHERE job_id=$1 ORDER BY created_at",job_id)
    artifacts=await db.pool.fetch("SELECT * FROM forge_artifacts WHERE job_id=$1 ORDER BY created_at DESC",job_id)
    return {'job':record(job),'events':[record(x) for x in reversed(events)],'messages':[record(x) for x in messages],'artifacts':[record(x) for x in artifacts]}

async def owned_job(job_id:uuid.UUID,request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")))
    if not await db.pool.fetchval("SELECT 1 FROM forge_jobs WHERE id=$1 AND user_id=$2",job_id,uid):
        raise HTTPException(404,"Forge job not found.")

@router.get("/jobs/{job_id}/events")
async def job_events(job_id:uuid.UUID,request:Request,after:int=0):
    await owned_job(job_id,request)
    rows=await db.pool.fetch("SELECT * FROM forge_job_events WHERE job_id=$1 AND id>$2 ORDER BY id LIMIT 500",job_id,max(0,after))
    return [record(x) for x in rows]

@router.get("/jobs/{job_id}/artifacts/{kind}")
async def job_artifact(job_id:uuid.UUID,kind:str,request:Request):
    await owned_job(job_id,request)
    if kind not in {"plan","diff","tests","log"}:raise HTTPException(400,"Unsupported Forge artifact type.")
    row=await db.pool.fetchrow("SELECT * FROM forge_artifacts WHERE job_id=$1 AND kind=$2 ORDER BY created_at DESC LIMIT 1",job_id,kind)
    if not row:raise HTTPException(404,"Forge artifact not available yet.")
    return record(row)

@router.post("/jobs/{job_id}/message")
async def message_job(job_id:uuid.UUID,data:MessageIn,request:Request):
    uid=uuid.UUID(await current_user(request,request.cookies.get("raven_session")))
    row=await db.pool.fetchrow("SELECT status FROM forge_jobs WHERE id=$1 AND user_id=$2",job_id,uid)
    if not row:raise HTTPException(404,"Forge job not found.")
    await db.pool.execute("INSERT INTO forge_messages(job_id,role,content) VALUES($1,'user',$2)",job_id,data.content)
    await event(job_id,'constraint_added',row['status'],data.content[:500],{})
    return {'ok':True}

async def control(job_id:uuid.UUID,uid:uuid.UUID,action:str,iterations:int=0):
    row=await db.pool.fetchrow("SELECT * FROM forge_jobs WHERE id=$1 AND user_id=$2",job_id,uid)
    if not row:raise HTTPException(404,"Forge job not found.")
    if action=='cancel':
        row=await db.pool.fetchrow("UPDATE forge_jobs SET cancel_requested=true,status=CASE WHEN status IN ('queued','paused','blocked') THEN 'cancelled' ELSE status END,updated_at=now() WHERE id=$1 RETURNING *",job_id)
    elif action=='pause':row=await db.pool.fetchrow("UPDATE forge_jobs SET pause_requested=true,status=CASE WHEN status='queued' THEN 'paused' ELSE status END,updated_at=now() WHERE id=$1 RETURNING *",job_id)
    elif action=='resume':row=await db.pool.fetchrow("UPDATE forge_jobs SET pause_requested=false,status='resuming',updated_at=now() WHERE id=$1 AND status IN ('paused','blocked','failed') RETURNING *",job_id)
    elif action=='continue':row=await db.pool.fetchrow("UPDATE forge_jobs SET pause_requested=false,cancel_requested=false,status='resuming',max_iterations=max_iterations+$2,updated_at=now() WHERE id=$1 RETURNING *",job_id,iterations)
    if not row:raise HTTPException(409,f"Job cannot {action} from its current state.")
    await event(job_id,'job_'+action,row['status'],f"Job {action} requested.",{'iterations':iterations})
    return record(row)

@router.post("/jobs/{job_id}/pause")
async def pause(job_id:uuid.UUID,request:Request):return await control(job_id,uuid.UUID(await current_user(request,request.cookies.get("raven_session"))),'pause')
@router.post("/jobs/{job_id}/resume")
async def resume(job_id:uuid.UUID,request:Request):return await control(job_id,uuid.UUID(await current_user(request,request.cookies.get("raven_session"))),'resume')
@router.post("/jobs/{job_id}/cancel")
async def cancel(job_id:uuid.UUID,request:Request):return await control(job_id,uuid.UUID(await current_user(request,request.cookies.get("raven_session"))),'cancel')
@router.post("/jobs/{job_id}/continue")
async def continue_job(job_id:uuid.UUID,data:ContinueIn,request:Request):return await control(job_id,uuid.UUID(await current_user(request,request.cookies.get("raven_session"))),'continue',data.iterations)

@router.post("/internal/events")
async def internal_event(data:EventIn,authorization:str=Header(default="")):
    if not _settings or not _settings.hermes_token or not hmac.compare_digest(authorization,"Bearer "+_settings.hermes_token):raise HTTPException(401,"Worker authentication required.")
    if not await db.pool.fetchval("SELECT 1 FROM forge_jobs WHERE id=$1",data.job_id):raise HTTPException(404,"Unknown Forge job.")
    await event(data.job_id,data.event_type,data.stage,data.summary,data.metadata)
    if data.stage in VALID_STATES:await db.pool.execute("UPDATE forge_jobs SET current_stage=$2,status=CASE WHEN status IN ('cancelled','paused') THEN status ELSE $2 END,updated_at=now() WHERE id=$1",data.job_id,data.stage)
    return {'ok':True}

async def event(job_id,event_type,stage,summary,metadata):
    await db.pool.execute("INSERT INTO forge_job_events(job_id,event_type,stage,summary,metadata) VALUES($1,$2,$3,$4,$5)",job_id,event_type,stage,summary[:2000],json.dumps(metadata or {}))

async def run_one(row):
    job_id=row['id'];project=await db.pool.fetchrow("SELECT * FROM forge_projects WHERE id=$1",row['project_id'])
    messages=await db.pool.fetch("SELECT role,content FROM forge_messages WHERE job_id=$1 ORDER BY created_at",job_id)
    await db.pool.execute("UPDATE forge_jobs SET status='initializing',current_stage='initializing',started_at=coalesce(started_at,now()),updated_at=now() WHERE id=$1",job_id)
    await event(job_id,'runtime_started','initializing','Hermes engineering runtime started.',{})
    payload={'job_id':str(job_id),'repo_path':project['repo_path'],'request':row['user_request'],'messages':[dict(x) for x in messages[-12:]],'execution_mode':row['execution_mode'],'provider_policy':row['provider_policy'],'model':row['selected_model'],'max_iterations':row['max_iterations'],'max_runtime_seconds':row['max_runtime_seconds'],'callback_url':'http://raven:8080/api/forge/internal/events','callback_token':_settings.hermes_token}
    try:
        result=await hermes('/forge/run',payload,timeout=row['max_runtime_seconds']+60)
        latest=await db.pool.fetchrow("SELECT cancel_requested,pause_requested FROM forge_jobs WHERE id=$1",job_id)
        final='cancelled' if latest['cancel_requested'] else 'paused' if latest['pause_requested'] else result.get('status','completed')
        if final not in TERMINAL_STATES|{'blocked','paused'}:final='failed'
        await db.pool.execute("UPDATE forge_jobs SET status=$2,current_stage=$2,selected_provider=$3,selected_model=$4,branch=$5,base_commit=$6,current_iteration=$7,summary=$8,failure_reason=$9,completed_at=CASE WHEN $2=ANY($10::text[]) THEN now() ELSE completed_at END,updated_at=now() WHERE id=$1",job_id,final,result.get('provider',''),result.get('model',''),result.get('branch',''),result.get('base_commit',''),result.get('iterations',0),result.get('summary',''),result.get('error',''),list(TERMINAL_STATES))
        if result.get('summary'):await db.pool.execute("INSERT INTO forge_messages(job_id,role,content) VALUES($1,'assistant',$2)",job_id,result['summary'])
        for kind,label,content in [('diff','Git diff',result.get('diff','')),('tests','Test results',result.get('tests','')),('plan','Plan',result.get('plan','')),('logs','Runtime log',result.get('log',''))]:
            if content:await db.pool.execute("INSERT INTO forge_artifacts(job_id,kind,label,content) VALUES($1,$2,$3,$4)",job_id,kind,label,str(content)[:200000])
        await event(job_id,'job_'+final,final,result.get('summary') or f"Forge job {final}.",{})
    except Exception as exc:
        await db.pool.execute("UPDATE forge_jobs SET status='failed',current_stage='failed',failure_reason=$2,completed_at=now(),updated_at=now() WHERE id=$1",job_id,str(exc)[:1000])
        await event(job_id,'job_failed','failed','Forge runtime failed without losing saved job state.',{'error':str(exc)[:500]})

async def worker(stop:asyncio.Event):
    while not stop.is_set():
        row=await db.pool.fetchrow("SELECT * FROM forge_jobs WHERE status IN ('queued','resuming') AND NOT pause_requested AND NOT cancel_requested ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1")
        if row:await run_one(row)
        else:
            try:await asyncio.wait_for(stop.wait(),2)
            except asyncio.TimeoutError:pass
