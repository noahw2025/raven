import hashlib
import re
from datetime import datetime, timezone
from html import unescape
from urllib.parse import urlparse
import httpx


def plain(value:str)->str:
    return re.sub(r"\s+"," ",unescape(re.sub(r"<[^>]+>"," ",str(value or "")))).strip()


def fingerprint(provider:str,external_id:str,url:str,title:str,company:str)->str:
    stable=f"{provider}|{external_id}|{url.rstrip('/').lower()}|{title.lower()}|{company.lower()}"
    return hashlib.sha256(stable.encode()).hexdigest()


def score_job(title:str,description:str,location:str,skills:list[str],preferences:dict)->tuple[int,dict]:
    hay=f"{title} {description}".lower();matched=[];missing=[]
    for skill in skills[:80]:
        token=skill.strip()
        if not token:continue
        (matched if re.search(rf"\b{re.escape(token.lower())}\b",hay) else missing).append(token)
    skill_score=round(65*len(matched)/max(1,min(len(skills),12))) if skills else 25
    pref_text=" ".join(str(x) for x in preferences.values()).lower()
    title_tokens={x for x in re.findall(r"[a-z0-9+#.]{3,}",title.lower()) if x not in {"senior","junior","manager","specialist"}}
    title_score=min(20,5*sum(1 for x in title_tokens if x in pref_text)) if pref_text else 10
    remote_score=10 if "remote" in f"{location} {description[:400]}".lower() and "remote" in pref_text else 0
    completeness=5 if len(description)>=500 else 2
    score=max(0,min(100,skill_score+title_score+remote_score+completeness))
    return score,{"matched_skills":matched[:15],"missing_profile_skills":missing[:15],"skill_score":skill_score,"preference_score":title_score+remote_score,"description_complete":len(description)>=500,"method":"deterministic profile-to-description coverage; final package receives a separate model review"}


async def fetch_board(provider:str,tenant:str,company:str="") -> list[dict]:
    provider=provider.lower().strip();tenant=tenant.strip().strip("/")
    headers={"User-Agent":"RAVEN-Career/1.0","Accept":"application/json"}
    async with httpx.AsyncClient(timeout=30,follow_redirects=True,headers=headers) as client:
        if provider=="greenhouse":
            response=await client.get(f"https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs",params={"content":"true"});response.raise_for_status();raw=response.json().get("jobs",[])
            return [{"provider":provider,"external_id":str(x.get("id","")),"company":company or tenant,"title":x.get("title",""),"location":(x.get("location") or {}).get("name",""),"description":plain(x.get("content","")),"source_url":x.get("absolute_url",""),"apply_url":x.get("absolute_url",""),"posted_at":x.get("updated_at"),"workplace_type":"","salary":"","metadata":{"departments":[d.get("name") for d in x.get("departments",[])]}} for x in raw]
        if provider=="lever":
            response=await client.get(f"https://api.lever.co/v0/postings/{tenant}",params={"mode":"json"});response.raise_for_status();raw=response.json()
            return [{"provider":provider,"external_id":str(x.get("id","")),"company":company or tenant,"title":x.get("text",""),"location":(x.get("categories") or {}).get("location",""),"description":plain(x.get("descriptionPlain") or x.get("description","")),"source_url":x.get("hostedUrl",""),"apply_url":x.get("applyUrl") or x.get("hostedUrl",""),"posted_at":None,"workplace_type":x.get("workplaceType",""),"salary":plain(x.get("salaryDescriptionPlain","")),"metadata":{"team":(x.get("categories") or {}).get("team"),"commitment":(x.get("categories") or {}).get("commitment")}} for x in raw]
        if provider=="ashby":
            response=await client.get(f"https://api.ashbyhq.com/posting-api/job-board/{tenant}",params={"includeCompensation":"true"});response.raise_for_status();raw=response.json().get("jobs",[])
            return [{"provider":provider,"external_id":str(x.get("jobUrl") or x.get("applyUrl") or x.get("title","")),"company":company or tenant,"title":x.get("title",""),"location":x.get("location",""),"description":plain(x.get("descriptionPlain") or x.get("descriptionHtml","")),"source_url":x.get("jobUrl",""),"apply_url":x.get("applyUrl") or x.get("jobUrl",""),"posted_at":x.get("publishedAt"),"workplace_type":x.get("workplaceType",""),"salary":plain((x.get("compensation") or {}).get("compensationTierSummary","")),"metadata":{"department":x.get("department"),"team":x.get("team"),"employment_type":x.get("employmentType")}} for x in raw if x.get("isListed",True)]
    raise ValueError("Supported providers are greenhouse, lever, and ashby")


def matches(job:dict,query:str,location:str="",remote_only:bool=False)->bool:
    query_tokens=[x for x in re.findall(r"[a-z0-9+#.]{2,}",query.lower()) if x not in {"and","the","for","with"}]
    title=str(job.get('title','')).lower();hay=f"{title} {job.get('description','')}".lower()
    title_hits=sum(1 for x in query_tokens if x in title);all_hits=sum(1 for x in query_tokens if x in hay)
    # Search-index snippets frequently contain one generic token and are not
    # actually the requested role. Require title relevance plus broader
    # evidence for multi-token searches.
    if query_tokens and (title_hits<1 or all_hits<min(2,len(query_tokens))):return False
    if location and location.lower() not in f"{job.get('location','')} {hay[:500]}":return False
    if remote_only and "remote" not in f"{job.get('location','')} {job.get('workplace_type','')} {hay[:500]}".lower():return False
    return bool(job.get("title") and job.get("source_url") and len(job.get("description","") or "")>=100)


def is_job_detail_url(url:str)->bool:
    parsed=urlparse(url);host=(parsed.hostname or '').lower();path=parsed.path
    if parsed.scheme not in {'http','https'}:return False
    if host in {'linkedin.com','www.linkedin.com'}:return bool(re.fullmatch(r'/jobs/view/[^/]+/?',path))
    if host in {'boards.greenhouse.io','job-boards.greenhouse.io'}:return bool(re.fullmatch(r'/[^/]+/jobs/\d+/?',path))
    if host in {'jobs.lever.co','jobs.ashbyhq.com'}:return bool(re.fullmatch(r'/[^/]+/[0-9a-fA-F-]{20,}(?:/application|/apply)?/?',path))
    return False

def actionable_job(job)->bool:
    provider=job.get('source_provider') or job.get('provider') or 'manual'
    return provider=='manual' or provider in {'greenhouse','lever','ashby'} or is_job_detail_url(job.get('source_url',''))

def indexed_job(item:dict,query:str,location:str="")->dict|None:
    """Normalize only recognizable public job-detail links, not search noise."""
    url=str(item.get("url","") or "").strip();host=(urlparse(url).hostname or "").lower()
    if not is_job_detail_url(url):return None
    raw_title=plain(item.get("title",query));description=plain(item.get("content",""))
    title=re.split(r"\s+[|–—]\s+",raw_title,1)[0].strip()
    company=""
    parts=[x.strip() for x in re.split(r"\s+[|–—]\s+",raw_title) if x.strip()]
    if len(parts)>1:company=parts[1]
    provider="linkedin_public_index" if "linkedin.com" in host else ("greenhouse_public_index" if "greenhouse.io" in host else ("lever_public_index" if "lever.co" in host else "ashby_public_index"))
    job={"provider":provider,"external_id":url,"company":company or host,"title":title or query,"location":location,"description":description,"source_url":url,"apply_url":url,"posted_at":item.get("publishedDate") or item.get("published_date"),"workplace_type":"remote" if "remote" in description.lower() else "","salary":"","metadata":{"engine":item.get("engine","public_index"),"provenance":"public search result; verify on employer page"}}
    return job if matches(job,query,location,False) else None

async def hydrate_indexed_job(job:dict)->dict:
    """Replace search snippets with public ATS detail when the URL identifies it."""
    url=str(job.get("source_url",""));parsed=urlparse(url);host=(parsed.hostname or "").lower();parts=[x for x in parsed.path.split("/") if x]
    headers={"User-Agent":"RAVEN-Career/1.0","Accept":"application/json"}
    try:
        async with httpx.AsyncClient(timeout=20,follow_redirects=True,headers=headers) as client:
            if "greenhouse.io" in host and len(parts)>=3 and parts[-2]=="jobs" and parts[-1].isdigit():
                tenant=parts[-3];response=await client.get(f"https://boards-api.greenhouse.io/v1/boards/{tenant}/jobs/{parts[-1]}")
                response.raise_for_status();x=response.json()
                job.update(company=job.get("company") if job.get("company") not in {"boards.greenhouse.io","job-boards.greenhouse.io"} else tenant,title=x.get("title") or job["title"],location=(x.get("location") or {}).get("name",""),description=plain(x.get("content","")),posted_at=x.get("updated_at"),metadata={**job.get("metadata",{}),"detail_verified":"greenhouse_api"})
            elif host=="jobs.lever.co" and len(parts)>=2:
                response=await client.get(f"https://api.lever.co/v0/postings/{parts[0]}/{parts[1]}")
                response.raise_for_status();x=response.json()
                job.update(company=parts[0],title=x.get("text") or job["title"],location=(x.get("categories") or {}).get("location",""),description=plain(x.get("descriptionPlain") or x.get("description","")),workplace_type=x.get("workplaceType",""),metadata={**job.get("metadata",{}),"detail_verified":"lever_api"})
    except (httpx.HTTPError,ValueError,KeyError):
        job.setdefault("metadata",{})["detail_verified"]="search_snippet_only"
    return job


def normalize(job:dict)->dict:
    for key in ("company","title","location","description","source_url","apply_url","workplace_type","salary","external_id","provider"):
        job[key]=plain(job.get(key,"")) if key not in {"source_url","apply_url"} else str(job.get(key,""))[:3000]
    job["description"]=job["description"][:30000]
    job["fingerprint"]=fingerprint(job["provider"],job["external_id"],job["source_url"],job["title"],job["company"])
    return job
