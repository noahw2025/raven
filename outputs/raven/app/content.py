import re
from urllib.parse import urlparse
import httpx


def clean_hashtags(values) -> list[str]:
    if isinstance(values,str): values=re.split(r"[\s,]+",values)
    if not isinstance(values,list): return []
    out=[]
    for value in values:
        tag=re.sub(r"[^A-Za-z0-9_]","",str(value).lstrip("#"))[:40]
        if tag and tag.lower() not in {x.lower() for x in out}: out.append(tag)
    return out[:20]


def normalize_plan(payload: dict, count: int = 3) -> list[dict]:
    rows=payload.get("posts") if isinstance(payload,dict) else []
    if not isinstance(rows,list): rows=[]
    normalized=[]
    for index,row in enumerate(rows[:count],1):
        if not isinstance(row,dict): continue
        caption=str(row.get("caption","")).strip()[:2200]
        if not caption: continue
        normalized.append({
            "title":str(row.get("title") or f"Concept {index}").strip()[:160],
            "caption":caption,
            "hashtags":clean_hashtags(row.get("hashtags",[])),
            "asset_prompt":str(row.get("asset_prompt") or row.get("visual_brief") or "").strip()[:3000],
            "format":str(row.get("format") or "image").lower()[:30],
            "rationale":str(row.get("rationale") or "").strip()[:1000],
        })
    return normalized


def is_public_media_url(value: str) -> bool:
    try:
        parsed=urlparse(value)
        host=(parsed.hostname or "").lower()
        return parsed.scheme=="https" and bool(host) and host not in {"localhost","127.0.0.1","::1"} and not host.endswith(".local")
    except ValueError:
        return False


class InstagramPublisher:
    def __init__(self,settings): self.s=settings

    def readiness(self) -> dict:
        configured=bool(self.s.instagram_user_id and self.s.instagram_access_token)
        return {
            "status":"connected" if configured else "setup_required",
            "configured":configured,
            "publishing_enabled":bool(configured and self.s.instagram_publish_enabled),
            "account_id_present":bool(self.s.instagram_user_id),
            "token_present":bool(self.s.instagram_access_token),
            "token_location":"server environment only",
            "requirements":["Instagram Professional account","Meta app and approved publish permission","server-side access token","public HTTPS media URL","RAVEN approval before publish"],
        }

    async def verify(self) -> dict:
        if not self.readiness()["configured"]: return self.readiness()
        url=f"{self.s.instagram_api_base.rstrip('/')}/{self.s.instagram_api_version}/{self.s.instagram_user_id}"
        async with httpx.AsyncClient(timeout=15) as client:
            response=await client.get(url,params={"fields":"id,username,account_type","access_token":self.s.instagram_access_token})
        if response.is_error: return {**self.readiness(),"status":"error","verified":False,"http_status":response.status_code,"error":"Meta rejected the server-side credential check"}
        data=response.json()
        return {**self.readiness(),"status":"connected","verified":True,"account":{"id":data.get("id",""),"username":data.get("username",""),"account_type":data.get("account_type","")}}

    async def publish_image(self,media_url: str,caption: str) -> dict:
        ready=self.readiness()
        if not ready["publishing_enabled"]: raise RuntimeError("Instagram publishing is not enabled on the server")
        if not is_public_media_url(media_url): raise ValueError("Instagram requires a public HTTPS media URL")
        base=f"{self.s.instagram_api_base.rstrip('/')}/{self.s.instagram_api_version}/{self.s.instagram_user_id}"
        auth={"access_token":self.s.instagram_access_token}
        async with httpx.AsyncClient(timeout=30) as client:
            container=await client.post(base+"/media",data={**auth,"image_url":media_url,"caption":caption[:2200]})
            container.raise_for_status(); creation_id=container.json().get("id")
            if not creation_id: raise RuntimeError("Meta did not return a media container id")
            published=await client.post(base+"/media_publish",data={**auth,"creation_id":creation_id})
            published.raise_for_status(); media_id=published.json().get("id")
        return {"provider":"instagram","container_id":creation_id,"media_id":media_id,"verified":bool(media_id)}


class XPublisher:
    def __init__(self,settings): self.s=settings

    def readiness(self)->dict:
        configured=bool(self.s.x_access_token)
        return {"status":"connected" if configured else "setup_required","configured":configured,"publishing_enabled":bool(configured and self.s.x_publish_enabled),"token_present":configured,"token_location":"server environment only","requirements":["X developer project and app","OAuth 2.0 user-context token with tweet.write","server-side token","RAVEN approval before publish"]}

    async def publish_text(self,text:str)->dict:
        if not self.readiness()["publishing_enabled"]:raise RuntimeError("X publishing is not enabled on the server")
        async with httpx.AsyncClient(timeout=20) as client:
            response=await client.post("https://api.x.com/2/tweets",headers={"Authorization":f"Bearer {self.s.x_access_token}"},json={"text":text[:280]})
        response.raise_for_status();data=response.json().get("data",{});post_id=data.get("id","")
        return {"provider":"x","post_id":post_id,"text":data.get("text",text[:280]),"verified":bool(post_id)}


def youtube_readiness(settings)->dict:
    configured=bool(settings.youtube_client_id and settings.youtube_client_secret and settings.youtube_refresh_token)
    return {"status":"connected" if configured else "setup_required","configured":configured,"publishing_enabled":bool(configured and settings.youtube_publish_enabled),"credential_location":"server environment only","adapter_status":"metadata and OAuth contract ready; resumable video upload pending","requirements":["Google Cloud project","YouTube Data API enabled","OAuth user consent","youtube.upload scope","server-side refresh token","video artifact","RAVEN approval before upload"]}
