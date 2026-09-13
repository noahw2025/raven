import asyncio
import ipaddress
import json
import hashlib
import logging
import re
import socket
import time
import uuid
from datetime import datetime
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup
from .db import db

logger=logging.getLogger("raven.research")


def source_quality(hostname:str,url:str="",title:str="")->str:
    """Explainable source tier used for ordering and the evidence ledger."""
    host=(hostname or "").lower().strip(".");text=f"{url} {title}".lower()
    if host.endswith(".gov") or host.endswith(".mil") or host.endswith(".edu"):return "institutional_primary"
    if host in {"arxiv.org","doi.org","pubmed.ncbi.nlm.nih.gov"}:return "research_primary"
    if host=="github.com" or host.endswith(".github.com") or any(part in host for part in ("developer.","developers.","docs.","documentation.")):return "technical_primary"
    if any(token in text for token in ("official documentation","official docs","api reference")):return "official_candidate"
    if host.endswith(("reuters.com","apnews.com","bbc.com","npr.org")):return "reputable_secondary"
    return "web_source"


SOURCE_RANK={"institutional_primary":0,"research_primary":1,"technical_primary":2,"official_candidate":3,"reputable_secondary":4,"web_source":5}


def compact_subject(objective:str,limit:int=18)->str:
    """Turn an instruction-shaped objective into a search-engine-shaped subject."""
    stop={"research","find","analyze","investigate","current","latest","official","including","include","give","provide","overview","detailed","deep","information","facts","recommended","recommendation"}
    words=re.findall(r"[A-Za-z0-9][A-Za-z0-9.+#/-]*",objective);chosen=[];seen=set()
    for word in words:
        key=word.casefold().strip("-/. ")
        if len(key)<2 or key in stop or key in seen:continue
        seen.add(key);chosen.append(word)
        if len(chosen)>=limit:break
    return " ".join(chosen) or objective[:180]


def official_query(subject:str)->str:
    low=subject.lower()
    if "instagram" in low:return "site:developers.facebook.com/docs/instagram-platform Instagram API content publishing"
    if "openai" in low:return f"site:platform.openai.com/docs {subject}"
    if "nist" in low:return f"site:nist.gov {subject}"
    if "youtube" in low:return f"site:developers.google.com/youtube {subject}"
    return f"{subject} official documentation"


def evidence_card(text:str,objective:str,limit:int=1100)->str:
    """Select fact-dense, query-relevant sentences instead of page boilerplate."""
    clean=re.sub(r"\s+"," ",text or "").strip()
    if not clean:return ""
    terms={word for word in re.findall(r"[a-z0-9]{4,}",objective.lower()) if word not in {"research","current","about","official","information","requirements","latest","publicly","available"}}
    sentences=[x.strip() for x in re.split(r"(?<=[.!?])\s+",clean) if len(x.strip())>=35]
    scored=[]
    for index,sentence in enumerate(sentences[:220]):
        low=sentence.lower();overlap=sum(1 for term in terms if term in low)
        fact_signal=2 if re.search(r"\b(?:must|required|supports?|limit|maximum|minimum|eligible|available|released|announced|reported|found|increased|decreased|percent|20\d{2})\b",low) else 0
        number_signal=1 if re.search(r"\d|%|\$",sentence) else 0
        boilerplate=-3 if re.search(r"\b(?:sign in|cookie|skip to content|privacy policy|all rights reserved|subscribe)\b",low) else 0
        scored.append((overlap*3+fact_signal+number_signal+boilerplate,index,sentence))
    chosen=sorted(sorted(scored,reverse=True)[:6],key=lambda item:item[1])
    card=" ".join(item[2] for item in chosen if item[0]>0)
    return (card or clean[:limit])[:limit]


def diverse_candidates(candidates:list[dict],limit:int)->list[dict]:
    ordered=sorted(candidates,key=lambda item:SOURCE_RANK[item["quality"]]);selected=[];hosts={}
    for item in ordered:
        host=(urlparse(item["url"]).hostname or "").lower();count=hosts.get(host,0)
        if count>=3:continue
        selected.append(item);hosts[host]=count+1
        if len(selected)>=limit:break
    return selected


async def structured_with_retry(ai,system:str,prompt:str,max_tokens:int,timeout:int):
    """Retry one transient local model swap/JSON failure before safe fallback."""
    last_error=None
    for attempt in range(2):
        try:return await ai.research_structured(system,prompt,max_tokens,timeout)
        except Exception as exc:
            last_error=exc
            if attempt==0:await asyncio.sleep(2)
    raise RuntimeError(f"structured generation failed after retry: {type(last_error).__name__}: {str(last_error)[:160]}") from last_error


def normalize_plan(payload:dict,objective:str,depth:int)->dict:
    raw=payload.get("queries",[]) if isinstance(payload,dict) else []
    queries=[]
    for item in raw:
        if isinstance(item,str): query,rationale=item,""
        elif isinstance(item,dict): query,rationale=str(item.get("query","")).strip(),str(item.get("rationale","")).strip()
        else: continue
        if query and query.casefold() not in {x["query"].casefold() for x in queries}:queries.append({"query":query[:500],"rationale":rationale[:500]})
    target={1:6,2:9,3:12}[depth]
    if not queries:queries=[{"query":objective[:500],"rationale":"Primary question"}]
    return {"queries":queries[:target],"sections":[str(x)[:200] for x in payload.get("sections",[])[:8] if str(x).strip()],"method":str(payload.get("method","multi-source current web research"))[:500]}


def normalize_synthesis(payload:dict)->dict:
    report=str(payload.get("report_markdown") or payload.get("report") or "").strip()[:50000]
    findings=[]
    for item in payload.get("findings",[])[:30] if isinstance(payload.get("findings",[]),list) else []:
        if not isinstance(item,dict):continue
        claim=str(item.get("claim","")).strip()[:4000]
        if not claim:continue
        try:confidence=max(0,min(1,float(item.get("confidence",0))))
        except (TypeError,ValueError):confidence=0
        indexes=[]
        for value in item.get("source_indexes",[]):
            try:index=int(value)
            except (TypeError,ValueError):continue
            if index>0 and index not in indexes:indexes.append(index)
        findings.append({"claim":claim,"confidence":confidence,"source_indexes":indexes[:10],"caveat":str(item.get("caveat","")).strip()[:2000]})
    return {"report":report,"findings":findings}


def report_quality(report:str,findings:list[dict],source_count:int,depth:int)->tuple[bool,dict]:
    """Mechanical floor: link lists and ungrounded prose can never be completed reports."""
    citations={int(x) for x in re.findall(r"\[S(\d+)\]",report or "")}
    valid={x for x in citations if 1<=x<=source_count}
    checks={
        "enough_detail":len(report or "")>={1:900,2:1600,3:2400}[depth],
        "enough_findings":len(findings)>={1:3,2:5,3:7}[depth],
        "citation_diversity":len(valid)>=min(4,source_count),
        "organized":len(re.findall(r"(?m)^#{1,3}\s+",report or ""))>=4,
        "not_link_dump":not bool(re.search(r"extractive (?:evidence set|fallback)|follow the \[S#\] links|source snippets",report or "",re.I)),
        "valid_citations":citations==valid,
    }
    return all(checks.values()),{"score":round(sum(checks.values())/len(checks),2),"checks":checks,"citations":sorted(valid),"characters":len(report or "")}


async def create_project(user_id:uuid.UUID,title:str,objective:str,depth:int=2)->uuid.UUID:
    pid=await db.pool.fetchval("INSERT INTO research_projects(user_id,title,objective,depth) VALUES($1,$2,$3,$4) RETURNING id",user_id,title[:240],objective[:12000],max(1,min(3,depth)))
    await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.queued',$3)",user_id,pid,json.dumps({"depth":depth}))
    return pid


def _public_host(hostname:str)->bool:
    if not hostname or hostname.lower() in {"localhost","host.docker.internal"} or hostname.lower().endswith(".local"):return False
    try:
        addresses={row[4][0] for row in socket.getaddrinfo(hostname,None)}
        return bool(addresses) and all(not (ipaddress.ip_address(x).is_private or ipaddress.ip_address(x).is_loopback or ipaddress.ip_address(x).is_reserved or ipaddress.ip_address(x).is_link_local) for x in addresses)
    except (socket.gaierror,ValueError):return False


async def fetch_public_page(url:str)->str:
    parsed=urlparse(url)
    if parsed.scheme not in {"http","https"} or not await asyncio.to_thread(_public_host,parsed.hostname or ""):return ""
    try:
        async with httpx.AsyncClient(timeout=12,follow_redirects=True,headers={"User-Agent":"RAVEN-Research/1.0"}) as client:response=await client.get(url)
        final=urlparse(str(response.url))
        if not await asyncio.to_thread(_public_host,final.hostname or "") or response.is_error:return ""
        if "text/html" not in response.headers.get("content-type",""):return ""
        soup=BeautifulSoup(response.text[:1_500_000],"html.parser")
        for node in soup(["script","style","nav","footer","form","noscript","svg"]):node.decompose()
        return re.sub(r"\s+"," ",soup.get_text(" ",strip=True)).strip()[:7000]
    except (httpx.HTTPError,ValueError):return ""


active_projects = {}

async def cancel_project(uid, pid):
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            row=await conn.fetchrow("SELECT status FROM research_projects WHERE id=$1 AND user_id=$2 FOR UPDATE",pid,uid)
            if not row or row['status'] in {'completed','failed','cancelled'}:return False
            task=active_projects.get(pid)
            if task:task.cancel()
            await conn.execute("UPDATE research_projects SET status='cancelled',finished_at=now(),updated_at=now() WHERE id=$1",pid)
            await conn.execute("INSERT INTO research_events(user_id,project_id,event) VALUES($1,$2,'research.cancelled')",uid,pid)
    return True

async def research_worker(ai,stop:asyncio.Event):
    while not stop.is_set():
        try:
            project=await claim_project()
            if project:
                task=asyncio.create_task(run_project(ai,project));active_projects[project['id']]=task
                try:await task
                except asyncio.CancelledError:
                    if asyncio.current_task().cancelling():raise
                finally:active_projects.pop(project['id'],None)
            else:await asyncio.wait_for(stop.wait(),timeout=1.5)
        except asyncio.TimeoutError:pass
        except Exception:await asyncio.sleep(1)


async def claim_project():
    async with db.pool.acquire() as conn:
        async with conn.transaction():
            row=await conn.fetchrow("SELECT * FROM research_projects WHERE status='queued' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1")
            if row:
                await conn.execute("UPDATE research_projects SET status='planning',started_at=now(),updated_at=now() WHERE id=$1",row["id"])
                await conn.execute("INSERT INTO research_events(user_id,project_id,event) VALUES($1,$2,'research.started')",row["user_id"],row["id"])
            return row


async def _run_project_legacy(ai,project):
    pid,uid=project["id"],project["user_id"];total_in=total_out=0;total_cost=0.0;started=time.perf_counter()
    try:
        today=datetime.now().astimezone().date().isoformat()
        # Planning is deterministic so a slow or unavailable model cannot delay source collection.
        objective=project["objective"][:420]
        plan_payload={"queries":[{"query":objective,"rationale":"Direct objective"},{"query":f"{objective} official documentation requirements","rationale":"Primary sources"},{"query":f"{objective} current implementation security limitations","rationale":"Risks and counter-evidence"},{"query":f"{objective} architecture open source","rationale":"Implementation patterns"},{"query":f"{objective} recent changes {today[:4]}","rationale":"Recency check"}],"sections":["Current state","Requirements","Implementation","Risks","Recommendation"],"method":"deterministic source-diverse plan; model-independent"}
        from .ai import AIResult
        plan_usage=AIResult("")
        plan=normalize_plan(plan_payload,project["objective"],project["depth"]);total_in+=plan_usage.tokens_in;total_out+=plan_usage.tokens_out;total_cost+=plan_usage.cost
        await db.pool.execute("UPDATE research_projects SET status='searching',plan=$2,updated_at=now() WHERE id=$1",pid,json.dumps(plan))
        await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.plan_ready',$3)",uid,pid,json.dumps({"queries":len(plan["queries"]),"method":plan["method"]}))
        query_rows=[]
        for index,item in enumerate(plan["queries"],1):
            row=await db.pool.fetchrow("INSERT INTO research_queries(project_id,ordinal,query,rationale,status) VALUES($1,$2,$3,$4,'running') RETURNING *",pid,index,item["query"],item["rationale"]);query_rows.append(row)
        async def search(row):
            try:
                return row,await ai.search_results(row["query"],6),""
            except Exception as exc:return row,[],str(exc)[:500]
        batches=await asyncio.gather(*(search(row) for row in query_rows));candidates=[]
        for row,results,error in batches:
            await db.pool.execute("UPDATE research_queries SET status=$2,result_count=$3,error=$4 WHERE id=$1",row["id"],"completed" if results else "failed",len(results),error)
            for item in results:
                url=str(item.get("url","")).strip();title=str(item.get("title","")).strip();snippet=str(item.get("content","")).strip()
                if url and title and url not in {x["url"] for x in candidates}:
                    host=urlparse(url).hostname or "";quality=source_quality(host,url,title)
                    candidates.append({"query_id":row["id"],"title":title[:1000],"url":url[:4000],"snippet":snippet[:2500],"published":str(item.get("publishedDate") or item.get("published_date") or "")[:100],"quality":quality})
        # Prefer primary evidence while retaining discovery order inside a tier.
        candidates=sorted(candidates,key=lambda item:SOURCE_RANK[item["quality"]])[:max(8,project["depth"]*6)]
        sem=asyncio.Semaphore(4)
        async def enrich(item):
            async with sem:item["page"]=await fetch_public_page(item["url"])
            return item
        enriched=await asyncio.gather(*(enrich(item) for item in candidates));sources=[]
        for index,item in enumerate(enriched,1):
            excerpt=(item["page"] or item["snippet"])[:7000];host=urlparse(item["url"]).hostname or ""
            try:
                row=await db.pool.fetchrow("INSERT INTO research_sources(project_id,query_id,source_index,title,url,host,published_at,excerpt,fetched,quality) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING *",pid,item["query_id"],index,item["title"],item["url"],host,item["published"],excerpt,bool(item["page"]),item["quality"])
                sources.append(row)
            except Exception:continue
        if not sources:raise RuntimeError("No usable current sources were retrieved")
        await db.pool.execute("UPDATE research_projects SET status='synthesizing',source_count=$2,updated_at=now() WHERE id=$1",pid,len(sources))
        await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.sources_collected',$3)",uid,pid,json.dumps({"sources":len(sources),"queries":len(query_rows)}))
        corpus="\n\n".join(f"[S{x['source_index']}] {x['title']}\nURL: {x['url']}\nPUBLISHED: {x['published_at'] or 'unknown'}\nEXCERPT: {x['excerpt'][:900]}" for x in sources)
        synth_prompt=f"""Research objective: {project['objective']}
Today: {today}
Use only the supplied sources. Distinguish event date from publication date, current fact from historical background, and sourced fact from inference. Cite every important factual paragraph with [S#]. Include executive summary, timeline/current state when relevant, competing perspectives, uncertainties, and actionable conclusions.
SOURCES:
{corpus[:14000]}
Return JSON with report_markdown and findings (claim, confidence 0-1, source_indexes, caveat)."""
        try:
            payload,synth_usage=await structured_with_retry(ai,"You are RAVEN Deep Research: rigorous, current, source-grounded, and explicit about uncertainty. Be concise.",synth_prompt,600,75)
            synthesis=normalize_synthesis(payload)
        except Exception as synth_exc:
            logger.warning("Research synthesis model unavailable; using extractive report: %s: %s",type(synth_exc).__name__,str(synth_exc)[:200])
            source_lines=[];fallback_findings=[]
            for source in sources[:12]:
                excerpt=re.sub(r"\s+"," ",source["excerpt"]).strip()
                sentence=re.split(r"(?<=[.!?])\s+",excerpt)[0][:500] if excerpt else "No extractable page text; see the source directly."
                source_lines.append(f"- **[S{source['source_index']}] {source['title']}** — {sentence}")
                fallback_findings.append({"claim":sentence,"confidence":.55,"source_indexes":[source["source_index"]],"caveat":"Extractive fallback: verify in the linked source before consequential use."})
            report=f"# {project['title']}\n\n## Executive summary\n\nRAVEN collected {len(sources)} current sources for the stated objective. The local synthesis model exceeded its 60-second budget, so this report preserves a concise, citation-linked extractive evidence set instead of guessing or failing.\n\n## Source-grounded evidence\n\n"+"\n\n".join(source_lines)+"\n\n## Limitations\n\nThis fallback does not reconcile contradictions or infer conclusions. Publication dates may be unknown. Follow the [S#] links and rerun synthesis when more local model capacity is available."
            synthesis={"report":report,"findings":fallback_findings}
            from .ai import AIResult
            synth_usage=AIResult("")
        total_in+=synth_usage.tokens_in;total_out+=synth_usage.tokens_out;total_cost+=synth_usage.cost
        if len(synthesis["report"])<200:raise RuntimeError("Research synthesis returned no usable report")
        await db.pool.execute("UPDATE research_projects SET status='verifying',updated_at=now() WHERE id=$1",pid)
        await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.synthesis_ready',$3)",uid,pid,json.dumps({"findings":len(synthesis["findings"]),"report_chars":len(synthesis["report"])}))
        verify_prompt=f"""Audit this report against the source excerpts. Remove or qualify unsupported claims, preserve [S#] citations, correct source-index mistakes, and add a short Limitations section. Return JSON with report_markdown and revised findings.
REPORT:
{synthesis['report'][:14000]}
SOURCES:
{corpus[:10000]}"""
        try:
            verified_payload,verify_usage=await structured_with_retry(ai,"You are an evidence auditor. Never improve prose by adding unsourced facts. Be concise.",verify_prompt,450,60)
            verified=normalize_synthesis(verified_payload)
        except Exception as verify_exc:
            logger.warning("Research verification model unavailable; preserving cited synthesis: %s: %s",type(verify_exc).__name__,str(verify_exc)[:200])
            verified=synthesis
            from .ai import AIResult
            verify_usage=AIResult("")
        total_in+=verify_usage.tokens_in;total_out+=verify_usage.tokens_out;total_cost+=verify_usage.cost
        if len(verified["report"])<200:verified=synthesis
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                for index,finding in enumerate(verified["findings"],1):await conn.execute("INSERT INTO research_findings(project_id,ordinal,claim,confidence,source_indexes,caveat) VALUES($1,$2,$3,$4,$5,$6)",pid,index,finding["claim"],finding["confidence"],finding["source_indexes"],finding["caveat"])
                await conn.execute("UPDATE research_projects SET status='completed',report=$2,source_count=$3,finding_count=$4,input_tokens=$5,output_tokens=$6,cost_usd=$7,finished_at=now(),updated_at=now() WHERE id=$1",pid,verified["report"],len(sources),len(verified["findings"]),total_in,total_out,total_cost)
                await conn.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.completed',$3)",uid,pid,json.dumps({"sources":len(sources),"findings":len(verified["findings"]),"tokens":total_in+total_out,"cost_usd":total_cost,"elapsed_ms":round((time.perf_counter()-started)*1000)}))
                await conn.execute("INSERT INTO model_usage(user_id,channel,purpose,provider,model,input_tokens,output_tokens,cost_usd,latency_ms,prompt_chars,response_chars,context_manifest) VALUES($1,'research','deep research project',$2,$3,$4,$5,$6,$7,$8,$9,$10)",uid,"Ollama" if ai.local else "OpenAI",ai.s.content_text_model or ai.s.raven_model,total_in,total_out,total_cost,round((time.perf_counter()-started)*1000),len(project["objective"]),len(verified["report"]),json.dumps({"project_id":str(pid),"queries":len(query_rows),"sources":len(sources),"verification_pass":True,"secrets_included":False}))
        # Make a completed report immediately available to ordinary RAG and alert
        # the owner without forcing the voice session to poll a long-running job.
        try:
            from .ai import chunks
            report_chunks=chunks(verified["report"],size=1200,overlap=160)[:30]
            vectors=await ai.embed(report_chunks)
            checksum=hashlib.sha256((str(pid)+verified["report"]).encode()).hexdigest()
            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    document_id=await conn.fetchval("INSERT INTO documents(user_id,name,mime,sha256,status,summary) VALUES($1,$2,'text/markdown',$3,'ready',$4) ON CONFLICT(user_id,sha256) DO UPDATE SET summary=excluded.summary RETURNING id",uid,f"Deep Research — {project['title']}",checksum,f"Completed research with {len(sources)} sources and {len(verified['findings'])} findings")
                    await conn.execute("DELETE FROM chunks WHERE document_id=$1",document_id)
                    column="local_embedding" if ai.local else "embedding"
                    for ordinal,(content,vector) in enumerate(zip(report_chunks,vectors)):
                        await conn.execute(f"INSERT INTO chunks(document_id,user_id,ordinal,content,{column}) VALUES($1,$2,$3,$4,$5)",document_id,uid,ordinal,content,vector)
                    await conn.execute("INSERT INTO notifications(user_id,title,body,severity) VALUES($1,'Deep Research complete',$2,'success')",uid,f"{project['title']} — {len(sources)} sources, {len(verified['findings'])} findings. Ask RAVEN what the latest research found.")
        except Exception as index_exc:
            logger.warning("Research completed but report indexing failed: %s",type(index_exc).__name__)
    except Exception as exc:
        error=f"{type(exc).__name__}: {str(exc) or 'no provider detail'}"
        logger.exception("Research project %s failed",pid)
        await db.pool.execute("UPDATE research_projects SET status='failed',error=$2,input_tokens=$3,output_tokens=$4,cost_usd=$5,finished_at=now(),updated_at=now() WHERE id=$1",pid,error[:1000],total_in,total_out,total_cost)
        await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.failed',$3)",uid,pid,json.dumps({"error":error[:500]}))


async def run_project(ai,project):
    """Answer-first, multi-stage research pipeline with a strict completion gate."""
    pid,uid=project["id"],project["user_id"]
    if await db.pool.fetchval("SELECT status FROM research_projects WHERE id=$1",pid)=='cancelled':return
    total_in=total_out=0;total_cost=0.0;started=time.perf_counter();provider=model=""
    try:
        today=datetime.now().astimezone().date().isoformat();objective=project["objective"][:420];depth=project["depth"];subject=compact_subject(objective)
        plan_payload={"queries":[
            {"query":subject,"rationale":"Direct answer and terminology"},
            {"query":official_query(subject),"rationale":"Primary official source"},
            {"query":f"{subject} changes news {today[:4]}","rationale":"Current developments"},
            {"query":f"{subject} statistics limits benchmarks","rationale":"Quantitative evidence"},
            {"query":f"{subject} expert analysis","rationale":"Interpretation"},
            {"query":f"{subject} limitations failures errors","rationale":"Counter-evidence"},
            {"query":f"{subject} implementation architecture guide","rationale":"How it works"},
            {"query":f"{subject} case study results","rationale":"Real-world outcomes"},
            {"query":f"{subject} alternatives comparison","rationale":"Decision context"},
            {"query":f"{subject} timeline changes","rationale":"Chronology"},
            {"query":f"{subject} law regulation policy","rationale":"Governance"},
            {"query":f"{subject} contradictory evidence unresolved","rationale":"Uncertainty and gaps"},
        ],"sections":["Executive answer","Key findings","Current developments","Detailed analysis","Comparisons and timeline","Risks and unknowns","Recommendations"],"method":"source-diverse multi-query research with analysis, synthesis, and audit"}
        plan=normalize_plan(plan_payload,project["objective"],depth)
        await db.pool.execute("UPDATE research_projects SET status='searching',plan=$2,updated_at=now() WHERE id=$1",pid,json.dumps(plan))
        await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.plan_ready',$3)",uid,pid,json.dumps({"queries":len(plan["queries"]),"method":plan["method"]}))
        query_rows=[]
        for index,item in enumerate(plan["queries"],1):
            query_rows.append(await db.pool.fetchrow("INSERT INTO research_queries(project_id,ordinal,query,rationale,status) VALUES($1,$2,$3,$4,'running') RETURNING *",pid,index,item["query"],item["rationale"]))
        async def search(row):
            try:return row,await ai.search_results(row["query"],8),""
            except Exception as exc:return row,[],str(exc)[:500]
        batches=await asyncio.gather(*(search(row) for row in query_rows));candidates=[];seen=set()
        for row,results,error in batches:
            await db.pool.execute("UPDATE research_queries SET status=$2,result_count=$3,error=$4 WHERE id=$1",row["id"],"completed" if results else "failed",len(results),error)
            for item in results:
                url=str(item.get("url","")).strip();title=str(item.get("title","")).strip();snippet=str(item.get("content","")).strip()
                if not url or not title or url in seen:continue
                seen.add(url);host=urlparse(url).hostname or ""
                candidates.append({"query_id":row["id"],"title":title[:1000],"url":url[:4000],"snippet":snippet[:2500],"published":str(item.get("publishedDate") or item.get("published_date") or "")[:100],"quality":source_quality(host,url,title)})
        candidates=diverse_candidates(candidates,{1:12,2:20,3:28}[depth])
        sem=asyncio.Semaphore(5)
        async def enrich(item):
            async with sem:item["page"]=await fetch_public_page(item["url"])
            return item
        enriched=await asyncio.gather(*(enrich(item) for item in candidates));sources=[]
        for item in enriched:
            excerpt=evidence_card(item["page"] or item["snippet"],project["objective"],1800)
            if len(excerpt)<80:continue
            host=urlparse(item["url"]).hostname or "";index=len(sources)+1
            try:
                sources.append(await db.pool.fetchrow("INSERT INTO research_sources(project_id,query_id,source_index,title,url,host,published_at,excerpt,fetched,quality) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING *",pid,item["query_id"],index,item["title"],item["url"],host,item["published"],excerpt,bool(item["page"]),item["quality"]))
            except Exception:continue
        # Three independently retrieved sources can still support a strong
        # focused answer. The later citation and quality gate scales to the
        # actual source count and will reject a shallow or ungrounded report.
        if len(sources)<3:raise RuntimeError(f"Insufficient usable evidence: {len(sources)} sources")
        await db.pool.execute("UPDATE research_projects SET status='synthesizing',source_count=$2,updated_at=now() WHERE id=$1",pid,len(sources))
        await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.sources_collected',$3)",uid,pid,json.dumps({"sources":len(sources),"queries":len(query_rows)}))
        corpus="\n\n".join(f"[S{x['source_index']}] {x['title']}\nHOST: {x['host']} | PUBLISHED: {x['published_at'] or 'unknown'} | QUALITY: {x['quality']}\nEVIDENCE: {x['excerpt'][:1200]}" for x in sources)[:28000]
        budget=float(ai.s.raven_research_budget_usd)
        analysis_prompt=f"OBJECTIVE: {project['objective']}\nTODAY: {today}\nBuild an evidence map before writing. Use only the evidence cards. Identify the direct answer, key facts, themes, comparisons, chronology, disagreements, missing evidence, and best report structure. Propose focused follow_up_queries only for material gaps, contradictions, or promising leads discovered in the evidence. Never substitute a title or URL for a fact. Return JSON with direct_answer, key_facts, themes, comparisons, timeline, contradictions, gaps, follow_up_queries, recommended_structure.\n\nEVIDENCE CARDS:\n{corpus}"
        analysis,usage=await structured_with_retry(ai,"You are RAVEN's senior research analyst. Extract and reconcile evidence; do not write generic advice.",analysis_prompt,2400,240)
        total_in+=usage.tokens_in;total_out+=usage.tokens_out;total_cost+=usage.cost;provider=usage.provider;model=usage.model
        if total_cost>budget:raise RuntimeError(f"Research cost guard reached ${total_cost:.4f} (budget ${budget:.2f})")
        await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.analysis_ready',$3)",uid,pid,json.dumps({"provider":provider,"model":model,"cost_usd":total_cost}))
        # Evidence-driven second pass: strong research systems do not stop at
        # the initial query plan. Follow material gaps and contradictions found
        # by the analyst, while keeping breadth, source count, and context bound.
        raw_followups=analysis.get("follow_up_queries",[]) if isinstance(analysis,dict) else []
        followups=[]
        for value in raw_followups:
            query=str(value.get("query","") if isinstance(value,dict) else value).strip()
            if len(query)>=5 and query.lower() not in {x["query"].lower() for x in query_rows}:followups.append(query[:500])
        followups=followups[:{1:2,2:3,3:4}[depth]]
        if followups:
            await db.pool.execute("UPDATE research_projects SET status='searching',updated_at=now() WHERE id=$1",pid)
            follow_rows=[]
            for query in followups:
                follow_rows.append(await db.pool.fetchrow("INSERT INTO research_queries(project_id,ordinal,query,rationale,status) VALUES($1,$2,$3,'Evidence-driven follow-up','running') RETURNING *",pid,len(query_rows)+len(follow_rows)+1,query))
            follow_batches=await asyncio.gather(*(search(row) for row in follow_rows))
            follow_candidates=[]
            for row,results,error in follow_batches:
                await db.pool.execute("UPDATE research_queries SET status=$2,result_count=$3,error=$4 WHERE id=$1",row["id"],"completed" if results else "failed",len(results),error)
                for item in results:
                    url=str(item.get("url","")).strip();title=str(item.get("title","")).strip();snippet=str(item.get("content","")).strip()
                    if not url or not title or url in seen:continue
                    seen.add(url);host=urlparse(url).hostname or ""
                    follow_candidates.append({"query_id":row["id"],"title":title[:1000],"url":url[:4000],"snippet":snippet[:2500],"published":str(item.get("publishedDate") or item.get("published_date") or "")[:100],"quality":source_quality(host,url,title)})
            follow_candidates=diverse_candidates(follow_candidates,{1:4,2:6,3:8}[depth])
            followed=await asyncio.gather(*(enrich(item) for item in follow_candidates))
            for item in followed:
                excerpt=evidence_card(item["page"] or item["snippet"],project["objective"],1800)
                if len(excerpt)<80:continue
                host=urlparse(item["url"]).hostname or "";index=len(sources)+1
                try:sources.append(await db.pool.fetchrow("INSERT INTO research_sources(project_id,query_id,source_index,title,url,host,published_at,excerpt,fetched,quality) VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10) RETURNING *",pid,item["query_id"],index,item["title"],item["url"],host,item["published"],excerpt,bool(item["page"]),item["quality"]))
                except Exception:continue
            query_rows.extend(follow_rows)
            corpus="\n\n".join(f"[S{x['source_index']}] {x['title']}\nHOST: {x['host']} | PUBLISHED: {x['published_at'] or 'unknown'} | QUALITY: {x['quality']}\nEVIDENCE: {x['excerpt'][:1200]}" for x in sources)[:32000]
            await db.pool.execute("UPDATE research_projects SET status='synthesizing',source_count=$2,updated_at=now() WHERE id=$1",pid,len(sources))
            await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.follow_up_complete',$3)",uid,pid,json.dumps({"queries":len(followups),"total_sources":len(sources)}))
        target={1:"600-900",2:"900-1400",3:"1400-2000"}[depth];minimum={1:3,2:5,3:7}[depth]
        required_citation_count=min(4,len(sources))
        prompt=f"OBJECTIVE: {project['objective']}\nTODAY: {today}\nANALYST EVIDENCE MAP:\n{json.dumps(analysis)[:12000]}\n\nEVIDENCE CARDS:\n{corpus}\n\nWrite an answer-first report of {target} words. The first paragraph directly answers the objective. Use sections: Executive answer, Key findings, Current and notable developments (with dates), Detailed analysis, Comparisons or timeline when relevant, Risks / limitations / unknowns, and Conclusions / recommendations. Extract facts and explain meaning; do not present browsing narration, a bibliography, or a list of links as the answer. Cite factual claims inline with [S#] and substantively use at least {required_citation_count} distinct relevant evidence cards across the report. Before returning JSON, count the distinct [S#] markers and correct the draft if fewer than {required_citation_count} are present. Distinguish sourced fact, inference, and recommendation; explain source conflicts. Return JSON with report_markdown and at least {minimum} findings containing claim, confidence, source_indexes, caveat."
        prompt+="\nEVIDENCE RULES: Respect requests for official documentation. Third-party integration settings are not upstream model defaults. Never turn page publication dates into product release dates. Do not invent comparisons, benchmark figures, architecture details, sample sizes, or parameter recommendations. Cite substantive claims, including the executive answer. If evidence is absent, state that it is unknown rather than filling a required section with speculation."
        payload,usage=await structured_with_retry(ai,"You are RAVEN Deep Research, an expert report writer. Deliver a concrete answer, not search results.",prompt,{1:3400,2:5500,3:8500}[depth],300)
        synthesis=normalize_synthesis(payload);total_in+=usage.tokens_in;total_out+=usage.tokens_out;total_cost+=usage.cost;provider=usage.provider or provider;model=usage.model or model
        if total_cost>budget:raise RuntimeError(f"Research cost guard reached ${total_cost:.4f} (budget ${budget:.2f})")
        if not synthesis["report"]:raise RuntimeError("Research synthesis returned no report")
        await db.pool.execute("UPDATE research_projects SET status='verifying',input_tokens=$2,output_tokens=$3,cost_usd=$4,provider=$5,model=$6,updated_at=now() WHERE id=$1",pid,total_in,total_out,total_cost,provider,model)
        verify_prompt=f"Audit this report against the evidence cards. Correct or qualify unsupported claims, invalid citations, stale-date statements, and contradictions. Preserve useful detail and organization. Return JSON with report_markdown, findings, quality_score, issues.\nREPORT:\n{synthesis['report'][:30000]}\nEVIDENCE CARDS:\n{corpus}"
        audited_payload,usage=await structured_with_retry(ai,"You are an exacting evidence auditor. Remove unsupported comparisons, recommendations and numbers. Distinguish integration defaults from upstream behavior and page dates from event dates. Cite substantive executive-summary claims. Do not add facts absent from evidence.",verify_prompt,{1:3400,2:5500,3:8500}[depth],300)
        audited=normalize_synthesis(audited_payload);total_in+=usage.tokens_in;total_out+=usage.tokens_out;total_cost+=usage.cost;provider=usage.provider or provider;model=usage.model or model
        if total_cost>budget:raise RuntimeError(f"Research cost guard reached ${total_cost:.4f} (budget ${budget:.2f})")
        # Preserve the evidence audit, repairing only documented quality defects.
        audited_quality=report_quality(audited["report"],audited["findings"],len(sources),depth)
        # Never overwrite factual corrections just because the earlier draft was longer.
        passed,quality=audited_quality
        if not passed:
            repair_prompt=f"The answer-quality gate rejected this report: {json.dumps(quality)}. Repair the report without inventing facts. Preserve its useful analysis, ensure at least {minimum} concrete findings, cite at least {required_citation_count} distinct relevant evidence cards inline, and retain all required sections. Citations must support substantive claims; do not add a bibliography or citation-only padding. Before returning JSON, explicitly count distinct [S#] markers and do not return fewer than {required_citation_count}. Return JSON with report_markdown and findings containing claim, confidence, source_indexes, caveat.\nREPORT:\n{audited['report'][:30000]}\nEVIDENCE CARDS:\n{corpus}"
            repaired_payload,usage=await structured_with_retry(ai,"You are RAVEN's final research quality editor. Fix only documented quality defects and stay evidence-bound.",repair_prompt,{1:3400,2:5500,3:8500}[depth],300)
            audited=normalize_synthesis(repaired_payload);total_in+=usage.tokens_in;total_out+=usage.tokens_out;total_cost+=usage.cost;provider=usage.provider or provider;model=usage.model or model
            if total_cost>budget:raise RuntimeError(f"Research cost guard reached ${total_cost:.4f} (budget ${budget:.2f})")
            passed,quality=report_quality(audited["report"],audited["findings"],len(sources),depth)
        if not passed and not quality["checks"].get("citation_diversity",False):
            cited=sorted({int(x) for x in re.findall(r"\[S(\d+)\]",audited["report"])})
            preferred=[int(x["source_index"]) for x in sources if int(x["source_index"]) not in cited]
            requested=(cited+preferred)[:required_citation_count]
            citation_repair_prompt=f"This otherwise useful report failed only or primarily because it used too little of the collected evidence. Revise substantive claims so the report accurately uses at least {required_citation_count} distinct evidence cards, including relevant cards from this target set: {requested}. Never attach a citation to a claim it does not support. Do not add a bibliography, link list, or citation-only padding. Preserve every required section and at least {minimum} concrete findings. Before returning, count distinct inline [S#] markers and verify the count is at least {required_citation_count}. Return JSON with report_markdown and findings containing claim, confidence, source_indexes, caveat.\nREPORT:\n{audited['report'][:30000]}\nEVIDENCE CARDS:\n{corpus}"
            repaired_payload,usage=await structured_with_retry(ai,"You are RAVEN's evidence-coverage editor. Broaden grounded evidence use without inventing or padding.",citation_repair_prompt,{1:3400,2:5500,3:8500}[depth],300)
            audited=normalize_synthesis(repaired_payload);total_in+=usage.tokens_in;total_out+=usage.tokens_out;total_cost+=usage.cost;provider=usage.provider or provider;model=usage.model or model
            if total_cost>budget:raise RuntimeError(f"Research cost guard reached ${total_cost:.4f} (budget ${budget:.2f})")
            passed,quality=report_quality(audited["report"],audited["findings"],len(sources),depth)
        if not passed:raise RuntimeError(f"Answer-quality gate rejected report: {json.dumps(quality)}")
        async with db.pool.acquire() as conn:
            async with conn.transaction():
                for index,finding in enumerate(audited["findings"],1):await conn.execute("INSERT INTO research_findings(project_id,ordinal,claim,confidence,source_indexes,caveat) VALUES($1,$2,$3,$4,$5,$6)",pid,index,finding["claim"],finding["confidence"],finding["source_indexes"],finding["caveat"])
                await conn.execute("UPDATE research_projects SET status='completed',report=$2,source_count=$3,finding_count=$4,input_tokens=$5,output_tokens=$6,cost_usd=$7,provider=$8,model=$9,answer_quality='audited',finished_at=now(),updated_at=now() WHERE id=$1",pid,audited["report"],len(sources),len(audited["findings"]),total_in,total_out,total_cost,provider,model)
                await conn.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.completed',$3)",uid,pid,json.dumps({"sources":len(sources),"findings":len(audited["findings"]),"cost_usd":total_cost,"quality":quality,"elapsed_ms":round((time.perf_counter()-started)*1000)}))
                await conn.execute("INSERT INTO model_usage(user_id,channel,purpose,provider,model,input_tokens,output_tokens,cost_usd,latency_ms,prompt_chars,response_chars,context_manifest) VALUES($1,'research','deep research project',$2,$3,$4,$5,$6,$7,$8,$9,$10)",uid,provider,model,total_in,total_out,total_cost,round((time.perf_counter()-started)*1000),len(project["objective"]),len(audited["report"]),json.dumps({"project_id":str(pid),"queries":len(query_rows),"sources":len(sources),"phases":["search","evidence_map","synthesis","audit"],"quality":quality,"secrets_included":False}))
        try:
            from .ai import chunks
            report_chunks=chunks(audited["report"],size=1000,overlap=180)[:40];vectors=await ai.embed(report_chunks);checksum=hashlib.sha256((str(pid)+audited["report"]).encode()).hexdigest()
            async with db.pool.acquire() as conn:
                async with conn.transaction():
                    document_id=await conn.fetchval("INSERT INTO documents(user_id,name,mime,sha256,status,summary) VALUES($1,$2,'text/markdown',$3,'ready',$4) ON CONFLICT(user_id,sha256) DO UPDATE SET summary=excluded.summary RETURNING id",uid,f"Deep Research — {project['title']}",checksum,f"Audited research with {len(sources)} sources and {len(audited['findings'])} findings")
                    await conn.execute("DELETE FROM chunks WHERE document_id=$1",document_id);column="local_embedding" if ai.local else "embedding"
                    for ordinal,(content,vector) in enumerate(zip(report_chunks,vectors)):await conn.execute(f"INSERT INTO chunks(document_id,user_id,ordinal,content,{column}) VALUES($1,$2,$3,$4,$5)",document_id,uid,ordinal,content,vector)
                    await conn.execute("INSERT INTO notifications(user_id,title,body,severity) VALUES($1,'Deep Research complete',$2,'success')",uid,f"{project['title']} — answer ready from {len(sources)} sources. Ask RAVEN follow-up questions.")
        except Exception as index_exc:logger.warning("Research completed but report indexing failed: %s",type(index_exc).__name__)
    except Exception as exc:
        error=f"{type(exc).__name__}: {str(exc) or 'no provider detail'}";logger.exception("Research project %s failed",pid)
        await db.pool.execute("UPDATE research_projects SET status='failed',error=$2,input_tokens=$3,output_tokens=$4,cost_usd=$5,provider=$6,model=$7,answer_quality='rejected',finished_at=now(),updated_at=now() WHERE id=$1",pid,error[:1000],total_in,total_out,total_cost,provider,model)
        await db.pool.execute("INSERT INTO research_events(user_id,project_id,event,detail) VALUES($1,$2,'research.failed',$3)",uid,pid,json.dumps({"error":error[:500]}))
