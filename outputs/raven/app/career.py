import hashlib
import json
import re


def normalize_string_list(value, limit: int = 12, item_limit: int = 500) -> list[str]:
    if isinstance(value,str): value=[x.strip() for x in re.split(r"[,\n]",value)]
    if not isinstance(value,list): return []
    out=[]
    for item in value:
        clean=re.sub(r"\s+"," ",str(item)).strip()[:item_limit]
        if clean and clean.casefold() not in {x.casefold() for x in out}: out.append(clean)
    return out[:limit]


def normalize_application_package(payload: dict) -> dict:
    if not isinstance(payload,dict): payload={}
    resume=str(payload.get("resume_markdown") or "").strip()[:30000]
    cover=str(payload.get("cover_letter") or "").strip()[:12000]
    try: score=max(0,min(100,int(payload.get("match_score",0))))
    except (TypeError,ValueError): score=0
    answers=[]
    raw_answers=payload.get("answers",[])
    if isinstance(raw_answers,list):
        for item in raw_answers[:20]:
            if not isinstance(item,dict): continue
            question=str(item.get("question") or "").strip()[:1000]
            answer=str(item.get("answer") or "").strip()[:4000]
            if question and answer: answers.append({"question":question,"answer":answer,"basis":str(item.get("basis") or "candidate profile").strip()[:500]})
    return {"resume_markdown":resume,"cover_letter":cover,"match_score":score,"strengths":normalize_string_list(payload.get("strengths",[])),"gaps":normalize_string_list(payload.get("gaps",[])),"answers":answers,"positioning":str(payload.get("positioning") or "").strip()[:2000]}


def package_checksum(resume: str, cover_letter: str, answers: list[dict]) -> str:
    canonical=json.dumps({"resume":resume,"cover_letter":cover_letter,"answers":answers},sort_keys=True,separators=(",",":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def safe_filename(value: str) -> str:
    clean=re.sub(r"[^A-Za-z0-9._-]+","-",value).strip("-.")
    return (clean or "raven-resume")[:100]
