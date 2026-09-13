"""Private research-only Hermes boundary. No host filesystem or desktop access."""
import asyncio
import hmac
import json
import os
import re
import subprocess
import time
import xml.etree.ElementTree as ET
from html import escape, unescape
from urllib.parse import urlparse
import httpx
from pathlib import Path
import yaml
from fastapi import FastAPI, Header, HTTPException, Depends
from pydantic import BaseModel, Field

app=FastAPI(docs_url=None,redoc_url=None)
lock=asyncio.Lock()

def authorize(authorization:str=Header(default="")):
    token=os.environ.get("HERMES_TOKEN","")
    if not token or not hmac.compare_digest(authorization,"Bearer "+token):
        raise HTTPException(401,"Worker authentication required")

@app.get("/tools",dependencies=[Depends(authorize)])
def inventory():
    from model_tools import get_tool_definitions
    from toolsets import get_all_toolsets,get_toolset_info
    definitions=get_tool_definitions(enabled_toolsets=["web"],quiet_mode=True,skip_tool_search_assembly=True)
    skills=[]
    for path in sorted(Path('/hermes/skills').rglob('SKILL.md'))[:300]:
        try:
            raw=path.read_text(encoding='utf-8')[:12000]
            meta=yaml.safe_load(raw.split('---',2)[1]) if raw.startswith('---') else {}
            meta=meta if isinstance(meta,dict) else {}
            skills.append({'name':str(meta.get('name',path.parent.name))[:120],'description':str(meta.get('description','Bundled Hermes skill'))[:600],'status':'installed_not_enabled','group':path.relative_to('/hermes/skills').parts[0]})
        except (OSError,ValueError,yaml.YAMLError):continue
    enabled=["web"]
    toolsets=[]
    for name in sorted(get_all_toolsets()):
        info=get_toolset_info(name) or {}
        toolsets.append({"name":name,"description":str(info.get("description",""))[:300],"enabled":name in enabled,"tool_count":int(info.get("tool_count",0))})
    mcp=configured_mcp()
    return {"runtime":"Hermes","model":effective_model(),"reasoner_ready":bool(os.environ.get("OPENROUTER_API_KEY")),"skills":skills,"mcp":mcp,"mcp_status":f"{len(mcp)} server definition(s) configured; use Test connection to discover tools" if mcp else "No MCP servers configured. Add HERMES_MCP_SERVERS_JSON server-side, then restart Hermes.","toolsets":toolsets,"enabled_toolsets":enabled,"tools":[{"name":d["function"]["name"],"description":d["function"].get("description","")[:600],"status":"ready"} for d in definitions if d["function"]["name"] in {"web_search","web_extract"}],"restriction":"Research-only container. Shell, desktop, publishing and applications are not exposed. Bundled skills are inventory, not permission to execute."}

def configured_mcp():
    try:raw=json.loads(os.environ.get("HERMES_MCP_SERVERS_JSON","{}"))
    except json.JSONDecodeError:return []
    if not isinstance(raw,dict):return []
    result=[]
    for name,cfg in list(raw.items())[:20]:
        if isinstance(cfg,dict):
            result.append({"name":str(name)[:80],"url":str(cfg.get("url",""))[:500],"auth_configured":bool(cfg.get("header_env") and os.environ.get(str(cfg["header_env"]))),"status":"configured_not_tested"})
    return result

def mcp_config(name:str):
    try:raw=json.loads(os.environ.get("HERMES_MCP_SERVERS_JSON","{}"))
    except json.JSONDecodeError:return None
    value=raw.get(name) if isinstance(raw,dict) else None
    return value if isinstance(value,dict) else None

def parse_mcp_body(response:httpx.Response):
    content_type=response.headers.get("content-type","").lower()
    if "text/event-stream" in content_type:
        payloads=[]
        for line in response.text.splitlines():
            if line.startswith("data:"):
                try:payloads.append(json.loads(line[5:].strip()))
                except json.JSONDecodeError:continue
        return payloads[-1] if payloads else {}
    return response.json()

class MCPProbe(BaseModel):
    name:str=Field(min_length=1,max_length=80,pattern=r"^[A-Za-z0-9_.-]+$")

@app.post("/tools/mcp/probe",dependencies=[Depends(authorize)])
async def probe_mcp(data:MCPProbe):
    cfg=mcp_config(data.name)
    if not cfg:raise HTTPException(404,"That MCP server is not configured server-side")
    url=str(cfg.get("url","")).strip();parsed=urlparse(url)
    if parsed.scheme not in {"http","https"} or not parsed.hostname:
        raise HTTPException(409,"MCP URL must be an explicit HTTP or HTTPS endpoint")
    # Configuration is trusted server-side, but block loopback and link-local URLs;
    # Docker service names such as http://my-mcp:8000 remain supported.
    if parsed.hostname.lower() in {"localhost","127.0.0.1","0.0.0.0","::1","169.254.169.254"}:
        raise HTTPException(409,"Use the Docker service name, not a loopback or metadata address")
    headers={"Accept":"application/json, text/event-stream","Content-Type":"application/json"}
    header_env=str(cfg.get("header_env","")).strip()
    if header_env:
        secret=os.environ.get(header_env,"")
        if not secret:raise HTTPException(409,"Configured MCP authentication environment variable is missing")
        headers[str(cfg.get("header_name") or "Authorization")]=str(cfg.get("header_prefix","Bearer "))+secret
    initialize={"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-03-26","capabilities":{},"clientInfo":{"name":"RAVEN-Hermes","version":"1.0"}}}
    try:
        async with httpx.AsyncClient(timeout=20,follow_redirects=False) as client:
            first=await client.post(url,headers=headers,json=initialize);first.raise_for_status();init=parse_mcp_body(first)
            session=first.headers.get("mcp-session-id")
            if session:headers["Mcp-Session-Id"]=session
            await client.post(url,headers=headers,json={"jsonrpc":"2.0","method":"notifications/initialized"})
            listed=await client.post(url,headers=headers,json={"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}});listed.raise_for_status();body=parse_mcp_body(listed)
    except (httpx.HTTPError,ValueError) as exc:raise HTTPException(502,f"MCP handshake failed: {type(exc).__name__}")
    if init.get("error") or body.get("error"):raise HTTPException(502,"MCP server returned a JSON-RPC error")
    info=(init.get("result") or {}).get("serverInfo") or {};tools=(body.get("result") or {}).get("tools") or []
    safe=[{"name":str(t.get("name",''))[:120],"description":str(t.get("description",''))[:500]} for t in tools[:200] if isinstance(t,dict)]
    return {"ok":True,"name":data.name,"server":{"name":str(info.get('name',''))[:120],"version":str(info.get('version',''))[:80]},"tool_count":len(safe),"tools":safe}

class Probe(BaseModel):
    query:str=Field(default="RAVEN local agent architecture",min_length=2,max_length=300)

def relevant_rows(rows:list,query:str)->list:
    stop={"official","github","search","research","about","with","from","what","that","this","the","and","for","into"}
    terms={x for x in re.findall(r"[a-z0-9]+",query.lower()) if len(x)>=3 and x not in stop}
    if not terms:return rows
    return [row for row in rows if terms.intersection(set(re.findall(r"[a-z0-9]+",f"{row.get('title','')} {row.get('url','')} {row.get('content','')}".lower())))]

@app.post("/tools/web/probe",dependencies=[Depends(authorize)])
async def probe_web(data:Probe):
    def run():
        from tools.web_tools import web_search_tool
        return json.loads(web_search_tool(data.query,limit=3))
    try:result=await asyncio.wait_for(asyncio.to_thread(run),timeout=30)
    except Exception as exc:raise HTTPException(502,f"Hermes web_search probe failed: {type(exc).__name__}")
    rows=((result.get("data") or {}).get("web") or []) if isinstance(result,dict) else []
    rows=relevant_rows(rows,data.query)
    backend="hermes_web_search"
    if not rows:
        # Keyless metadata-only fallback when self-hosted engines are throttled.
        # It remains inside the Hermes boundary and is reported explicitly.
        try:
            async with httpx.AsyncClient(timeout=15,headers={"User-Agent":"RAVEN-Hermes/1.0"}) as client:
                response=await client.get("https://www.bing.com/search",params={"q":data.query,"format":"rss"})
            response.raise_for_status();root=ET.fromstring(response.text)
            rows=[{"title":unescape((item.findtext("title") or "").strip()),"url":(item.findtext("link") or "").strip()} for item in root.findall(".//item")[:3]]
            rows=relevant_rows([x for x in rows if x["title"] and re.match(r"^https?://",x["url"])],data.query)
            backend="bing_rss_keyless_fallback"
        except Exception:rows=[]
    if not rows:raise HTTPException(502,"Hermes search and its keyless fallback returned no verified results")
    return {"ok":True,"tool":"web_search","backend":backend,"result_count":len(rows),"results":[{"title":str(x.get("title",""))[:200],"url":str(x.get("url",""))[:500]} for x in rows]}

def effective_model():
    model=os.environ.get('OPENROUTER_MODEL','openrouter/free')
    return 'nvidia/nemotron-3-super-120b-a12b:free' if model=='openrouter/free' else model

class Research(BaseModel):
    topic:str=Field(min_length=2,max_length=6000)

def research_sync(topic):
    from run_agent import AIAgent
    model=effective_model()
    if model!="openrouter/free" and not model.endswith(":free"):raise ValueError("Free model required")
    agent=AIAgent(base_url="https://openrouter.ai/api/v1",api_key=os.environ["OPENROUTER_API_KEY"],model=model,enabled_toolsets=["web"],max_iterations=8,max_tokens=2400,quiet_mode=True,save_trajectories=False)
    result=agent.run_conversation(user_message=topic,system_message="Research this topic using public web evidence. Return an organized answer with specific findings, uncertainty and source citations. Never claim evidence was found unless returned by tools. Do not perform external writes.")
    return {"summary":result.get("final_response") or "Hermes returned no report.","provider":"OpenRouter","model":model}

@app.post("/research",dependencies=[Depends(authorize)])
async def research(data:Research):
    if not os.environ.get("OPENROUTER_API_KEY"):raise HTTPException(503,"Set the server-side OpenRouter key before running Hermes research.")
    if lock.locked():raise HTTPException(409,"Hermes is already researching. Wait for that task to finish.")
    async with lock:
        try:return await asyncio.to_thread(research_sync,data.topic)
        except Exception:raise HTTPException(502,"Hermes research failed; no local fallback was started.")

# ---------------------------------------------------------------------------
# Forge: authenticated, workspace-contained Hermes engineering runtime.
# RAVEN owns durable jobs and approvals. Hermes owns the agent/tool loop.
# ---------------------------------------------------------------------------
WORKSPACE_ROOT=Path(os.environ.get("FORGE_WORKSPACE_ROOT","/workspace")).resolve()
EXTERNAL_PROJECTS_ROOT=Path(os.environ.get("FORGE_EXTERNAL_PROJECTS_ROOT","/external-projects")).resolve()
forge_lock=asyncio.Lock()

class ForgeInspect(BaseModel):repo_path:str=Field(min_length=1,max_length=500)
class ForgeProjectCreate(BaseModel):
    slug:str=Field(pattern=r"^[a-z0-9][a-z0-9-]{0,78}[a-z0-9]$|^[a-z0-9]$")
    display_name:str=Field(min_length=1,max_length=120)
    template:str=Field("website",pattern="^(website|blank|python)$")
    default_branch:str=Field("main",pattern=r"^[A-Za-z0-9._/-]{1,120}$")
class ForgeRun(BaseModel):
    job_id:str=Field(min_length=36,max_length=36)
    repo_path:str=Field(min_length=1,max_length=500)
    request:str=Field(min_length=3,max_length=20000)
    messages:list[dict]=Field(default_factory=list,max_length=20)
    execution_mode:str=Field(pattern="^(ask|plan|build|autonomous)$")
    provider_policy:str=Field(pattern="^(auto|local|openrouter|nvidia|codex)$")
    model:str=Field("",max_length=200)
    max_iterations:int=Field(12,ge=1,le=40)
    max_runtime_seconds:int=Field(1800,ge=60,le=14400)
    callback_url:str=Field(pattern=r"^http://raven:8080/api/forge/internal/events$")
    callback_token:str=Field(min_length=32,max_length=500)

def forge_path(relative:str)->Path:
    relative=relative.replace('\\','/').strip().strip('/') or '.'
    if '..' in Path(relative).parts or Path(relative).is_absolute():raise HTTPException(400,"Path traversal is blocked.")
    if relative.startswith('external/'):
        child=relative.removeprefix('external/')
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,78}[a-z0-9]|[a-z0-9]",child):raise HTTPException(400,"Invalid external project ID.")
        root=EXTERNAL_PROJECTS_ROOT;target=(root/child).resolve()
    else:root=WORKSPACE_ROOT;target=(root/relative).resolve()
    try:target.relative_to(root)
    except ValueError:raise HTTPException(400,"Project is outside the Forge workspace root.")
    if not target.is_dir():raise HTTPException(404,"Project directory is not mounted in Forge.")
    return target

def git(project:Path,*args:str,timeout:int=20)->str:
    try:return subprocess.run(["git",*args],cwd=project,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=timeout,check=False).stdout.strip()
    except (OSError,subprocess.SubprocessError):return ""

@app.get("/forge/providers",dependencies=[Depends(authorize)])
def forge_providers():
    local_model=os.environ.get("FORGE_LOCAL_MODEL","qwen3:8b")
    return {"runtime":"Hermes","providers":[
        {"id":"local","label":"Local Ollama","configured":True,"model":local_model,"cost":"local / $0 API","tool_capable":True},
        {"id":"openrouter","label":"OpenRouter","configured":bool(os.environ.get("OPENROUTER_API_KEY")),"model":os.environ.get("FORGE_OPENROUTER_MODEL",effective_model()),"cost":"provider pricing","tool_capable":True},
        {"id":"nvidia","label":"NVIDIA NIM","configured":bool(os.environ.get("NVIDIA_API_KEY")),"model":os.environ.get("FORGE_NVIDIA_MODEL",os.environ.get("NVIDIA_RESEARCH_MODEL","")),"cost":"NVIDIA account terms","tool_capable":True},
        {"id":"codex","label":"Codex (optional)","configured":False,"model":"","cost":"Codex allowance","tool_capable":True,"detail":"Not enabled in the isolated Forge container."}],
        "auto_order":["nvidia","openrouter","local"],"workspace_root":"approved Docker mount","secrets_exposed":False}

@app.post("/forge/projects/inspect",dependencies=[Depends(authorize)])
def inspect_forge_project(data:ForgeInspect):
    project=forge_path(data.repo_path);is_git=(project/'.git').exists()
    return {"exists":True,"is_git":is_git,"branch":git(project,"branch","--show-current") if is_git else "","base_commit":git(project,"rev-parse","HEAD") if is_git else "","dirty":bool(git(project,"status","--porcelain")) if is_git else False}

@app.post("/forge/projects/create",dependencies=[Depends(authorize)])
def create_forge_project(data:ForgeProjectCreate):
    root=EXTERNAL_PROJECTS_ROOT;root.mkdir(parents=True,exist_ok=True)
    project=(root/data.slug).resolve()
    try:project.relative_to(root)
    except ValueError:raise HTTPException(400,"Project escaped the external projects root.")
    created=not project.exists();project.mkdir(parents=False,exist_ok=True)
    if data.template=='website' and created:
        safe_name=escape(data.display_name)
        (project/'index.html').write_text(f'''<!doctype html>\n<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{safe_name}</title><link rel="stylesheet" href="styles.css"></head><body><main><p class="eyebrow">NEW PROJECT</p><h1>{safe_name}</h1><p>Ready for your first Forge build.</p><button id="action">Get started</button></main><script src="app.js"></script></body></html>\n''',encoding='utf-8')
        (project/'styles.css').write_text('''*{box-sizing:border-box}body{margin:0;min-height:100vh;display:grid;place-items:center;background:#07111f;color:#effcff;font:16px system-ui}main{width:min(720px,90vw);padding:56px;border:1px solid #2a6680;border-radius:24px;background:#0d1b30}h1{font-size:clamp(42px,8vw,80px);margin:.2em 0}.eyebrow{color:#66ecff;letter-spacing:.2em}button{padding:12px 18px;background:#68eadb;border:0;border-radius:8px;color:#082126;font-weight:700}\n''',encoding='utf-8')
        (project/'app.js').write_text("document.querySelector('#action').onclick=()=>alert('Your project is ready.');\n",encoding='utf-8')
    elif data.template=='python' and created:
        (project/'app.py').write_text("from fastapi import FastAPI\napp=FastAPI()\n@app.get('/')\ndef home(): return {'status':'ready'}\n",encoding='utf-8')
        (project/'requirements.txt').write_text('fastapi\nuvicorn[standard]\n',encoding='utf-8')
    if created:
        (project/'README.md').write_text(f"# {data.display_name}\n\nCreated by RAVEN Forge.\n",encoding='utf-8')
        (project/'.gitignore').write_text('.env\n.env.*\n__pycache__/\nnode_modules/\ndist/\n',encoding='utf-8')
        subprocess.run(['git','init','-b',data.default_branch],cwd=project,capture_output=True,text=True,timeout=20,check=False)
    return {"created":created,"repo_path":f"external/{data.slug}","slug":data.slug,"template":data.template,"is_git":(project/'.git').exists(),"branch":git(project,'branch','--show-current')}

def forge_provider(policy:str,model_override:str):
    candidates=[policy] if policy!='auto' else ['nvidia','openrouter','local']
    for provider in candidates:
        if provider=='nvidia' and os.environ.get('NVIDIA_API_KEY'):
            return provider,model_override or os.environ.get('FORGE_NVIDIA_MODEL') or os.environ.get('NVIDIA_RESEARCH_MODEL',''),"https://integrate.api.nvidia.com/v1",os.environ['NVIDIA_API_KEY']
        if provider=='openrouter' and os.environ.get('OPENROUTER_API_KEY'):
            return provider,model_override or os.environ.get('FORGE_OPENROUTER_MODEL') or effective_model(),"https://openrouter.ai/api/v1",os.environ['OPENROUTER_API_KEY']
        if provider=='local':
            return provider,model_override or os.environ.get('FORGE_LOCAL_MODEL','qwen3:8b'),os.environ.get('FORGE_OLLAMA_URL','http://ollama:11434/v1'),"ollama"
        if provider=='codex':raise HTTPException(503,"Codex is optional and is not enabled in this Forge runtime.")
    raise HTTPException(503,f"The selected Forge provider '{policy}' is not configured.")

def forge_run_sync(data:ForgeRun):
    from run_agent import AIAgent
    project=forge_path(data.repo_path);provider,model,base_url,key=forge_provider(data.provider_policy,data.model)
    started=time.monotonic();events=[]
    def emit(event_type,stage,summary,metadata=None):
        item={"job_id":data.job_id,"event_type":event_type,"stage":stage,"summary":str(summary)[:2000],"metadata":metadata or {}}
        events.append(item)
        try:httpx.post(data.callback_url,headers={"Authorization":"Bearer "+data.callback_token},json=item,timeout=4)
        except Exception:pass
    def agent_event(kind,payload):
        payload=payload if isinstance(payload,dict) else {"detail":str(payload)}
        name=str(payload.get('tool_name') or payload.get('name') or kind)
        stage='testing' if re.search(r"test|pytest|lint|build",name,re.I) else 'running'
        emit('tool_event',stage,name,{k:v for k,v in payload.items() if k not in {'content','reasoning','thinking','api_key'} and len(str(v))<2000})
    is_git=(project/'.git').exists();base_commit=git(project,'rev-parse','HEAD') if is_git else '';branch=git(project,'branch','--show-current') if is_git else ''
    dirty=bool(git(project,'status','--porcelain')) if is_git else False
    emit('inspection_started','inspecting',f"Inspecting {project.name}.",{'git':is_git,'dirty':dirty})
    if is_git and data.execution_mode in {'build','autonomous'} and not dirty:
        slug=re.sub(r'[^a-z0-9]+','-',data.request.lower()).strip('-')[:38] or 'task';candidate=f"raven/forge/{slug}-{data.job_id[:6]}"
        switched=subprocess.run(['git','switch','-c',candidate],cwd=project,capture_output=True,text=True,timeout=20,check=False)
        if switched.returncode==0:branch=candidate;emit('git_event','planning',f"Created isolated branch {branch}.",{})
    elif dirty:emit('warning','inspecting','Existing uncommitted work detected. Forge will preserve it and will not create a branch automatically.',{})
    history='\n'.join(f"{m.get('role','user').upper()}: {str(m.get('content',''))[:3000]}" for m in data.messages[-8:])
    mode_rules={
        'ask':'Read and explain only. Do not modify files or run commands that change state.',
        'plan':'Inspect and produce a concrete plan only. Do not modify files.',
        'build':'Implement one complete, bounded cycle and verify it. Preserve unrelated user changes.',
        'autonomous':'Iterate through failures until verified or the iteration/runtime limit is reached.'}[data.execution_mode]
    prompt=f"""You are the Hermes engineering runtime inside RAVEN Forge. Work only in the current project directory: {project}.
{mode_rules}
Never read .env, credentials, tokens, /proc environments, or files outside this project. Never push, force-reset, delete broad directories, install system packages, change OS services, or disable security. Dangerous commands must be denied. Use targeted search and reads, patch files carefully, run proportionate tests/builds, inspect failures, and iterate. Do not claim completion without observed verification. Do not expose private chain-of-thought; return a concise plan, work summary, verification evidence, changed files, and any genuine blocker.

JOB HISTORY / CONSTRAINTS:
{history}

CURRENT REQUEST:
{data.request}
"""
    old_cwd=os.getcwd();old_terminal=os.environ.get('TERMINAL_CWD');secrets={name:os.environ.pop(name,None) for name in ('OPENROUTER_API_KEY','NVIDIA_API_KEY','OPENAI_API_KEY','HERMES_TOKEN','HERMES_MCP_AUTH_TOKEN')}
    os.environ['TERMINAL_CWD']=str(project)
    try:
        try:
            from tools.terminal_tool import set_approval_callback
            set_approval_callback(lambda command,description,*args,**kwargs:'deny')
        except Exception:pass
        os.chdir(project);emit('plan_updated','planning','Hermes is mapping the repository and planning the change.',{})
        agent=AIAgent(base_url=base_url,api_key=key,provider=provider if provider!='local' else 'custom',requested_provider=provider if provider!='local' else 'custom',model=model,enabled_toolsets=['file','terminal','search','todo'],max_iterations=data.max_iterations,max_tokens=6000,quiet_mode=True,save_trajectories=False,skip_memory=True,skip_context_files=False,event_callback=agent_event)
        result=agent.run_conversation(user_message=prompt,system_message="RAVEN Forge engineering worker. Follow the workspace and safety boundary exactly.")
        final=str(result.get('final_response') or 'Hermes returned no final report.')
    finally:
        os.chdir(old_cwd)
        if old_terminal is None:os.environ.pop('TERMINAL_CWD',None)
        else:os.environ['TERMINAL_CWD']=old_terminal
        for name,value in secrets.items():
            if value is not None:os.environ[name]=value
    diff=git(project,'diff','--no-ext-diff','--')[:200000] if is_git else ''
    stat=git(project,'diff','--stat') if is_git else ''
    status='blocked' if re.search(r"\bblocked\b|need(?:s)? (?:your|user) approval",final,re.I) else 'completed'
    emit('verification','verifying','Hermes finished its loop; Forge captured the repository diff and final evidence.',{'diff_files':stat})
    return {'status':status,'provider':provider,'model':model,'runtime':'Hermes','iterations':data.max_iterations,'elapsed_seconds':round(time.monotonic()-started,2),'branch':branch,'base_commit':base_commit,'summary':final[:20000],'diff':diff,'tests':'Verification evidence is included in the Hermes final report and structured tool events.','plan':'See plan_updated and tool events.','log':'\n'.join(x['summary'] for x in events[-200:]),'error':''}

@app.post("/forge/run",dependencies=[Depends(authorize)])
async def run_forge(data:ForgeRun):
    if forge_lock.locked():raise HTTPException(409,"Another Forge engineering loop is active.")
    async with forge_lock:
        try:return await asyncio.wait_for(asyncio.to_thread(forge_run_sync,data),timeout=data.max_runtime_seconds)
        except asyncio.TimeoutError:raise HTTPException(408,"Forge reached its runtime limit; durable RAVEN job state is preserved.")
