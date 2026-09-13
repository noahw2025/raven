"""Minimal Windows host companion for RAVEN.

It accepts only fixed application IDs, never shell text, paths, or model-generated
arguments. Run it on the Windows host; the Docker backend authenticates with a
server-side bearer token.
"""
from __future__ import annotations

import hmac
import json
import os
import re
import shutil
import subprocess
import time
import ctypes
import csv
import io
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import quote, quote_plus, urlparse

TOKEN=os.environ.get("RAVEN_DESKTOP_BRIDGE_TOKEN","")
PORT=int(os.environ.get("RAVEN_DESKTOP_BRIDGE_PORT","8765"))
BIND=os.environ.get("RAVEN_DESKTOP_BRIDGE_BIND","127.0.0.1")
BRIDGE_VERSION="1.9"
PROJECTS_ROOT=Path(os.environ.get("RAVEN_PROJECTS_ROOT",os.path.expandvars(r"%USERPROFILE%\Documents\Codex\RAVEN-Projects"))).resolve()

APPS={
    "steam":{"label":"Steam","uri":"steam://open/main","executables":["steam.exe"],"paths":[r"C:\Program Files (x86)\Steam\steam.exe",r"C:\Program Files\Steam\steam.exe"]},
    "discord":{"label":"Discord","uri":"discord://-/channels/@me","executables":["Discord.exe"]},
    "chrome":{"label":"Google Chrome","executables":["chrome.exe"],"paths":[r"C:\Program Files\Google\Chrome\Application\chrome.exe",r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"]},
    "epic":{"label":"Epic Games Launcher","uri":"com.epicgames.launcher://store/","executables":["EpicGamesLauncher.exe"]},
    "apex":{"label":"Apex Legends","steam_app_id":"1172470","processes":["r5apex.exe","r5apex_dx12.exe","start_protected_game.exe"]},
    "spotify":{"label":"Spotify","uri":"spotify:","executables":["Spotify.exe"],"paths":[os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe")]},
    "chatgpt":{"label":"ChatGPT","uri":"https://chatgpt.com/","executables":[]},
    "youtube":{"label":"YouTube","uri":"https://www.youtube.com/","executables":[]},
}


def discover(app:dict)->str:
    for path in app.get("paths",[]):
        if os.path.isfile(path):return path
    for name in app.get("executables",[]):
        found=shutil.which(name)
        if found:return found
    return ""


def open_registered_target(target:str)->None:
    """Ask Windows Explorer to dispatch a fixed URI without blocking the bridge."""
    subprocess.Popen(["explorer.exe",target],close_fds=True)


def process_running(names:list[str])->bool:
    try:
        output=subprocess.run(["tasklist","/FO","CSV","/NH"],capture_output=True,text=True,timeout=5,check=False).stdout.lower()
    except (OSError,subprocess.SubprocessError):return False
    return any(f'"{name.lower()}"' in output for name in names)


def running_pids(names:list[str])->set[int]:
    wanted={name.lower() for name in names};result=set()
    try:
        output=subprocess.run(["tasklist","/FO","CSV","/NH"],capture_output=True,text=True,timeout=5,check=False).stdout
        for row in csv.reader(io.StringIO(output)):
            if len(row)>1 and row[0].lower() in wanted:
                try:result.add(int(row[1]))
                except ValueError:pass
    except (OSError,subprocess.SubprocessError):pass
    return result


def focus_process(names:list[str])->bool:
    """Restore and foreground a visible window owned by an allowlisted process."""
    pids=running_pids(names)
    if not pids:return False
    found=[]
    enum_proc=ctypes.WINFUNCTYPE(ctypes.c_bool,ctypes.c_void_p,ctypes.c_void_p)
    def visit(hwnd,_):
        pid=ctypes.c_ulong();ctypes.windll.user32.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
        if pid.value in pids and ctypes.windll.user32.IsWindowVisible(hwnd):found.append(hwnd);return False
        return True
    ctypes.windll.user32.EnumWindows(enum_proc(visit),0)
    if not found:return False
    ctypes.windll.user32.ShowWindow(found[0],9)
    return bool(ctypes.windll.user32.SetForegroundWindow(found[0]))


def wait_for_process(names:list[str],seconds:float)->bool:
    deadline=time.monotonic()+seconds
    while time.monotonic()<deadline:
        if process_running(names):return True
        time.sleep(0.75)
    return process_running(names)


def send_media_key(action:str)->None:
    virtual_keys={"next":0xB0,"previous":0xB1}
    key=virtual_keys[action]
    ctypes.windll.user32.keybd_event(key,0,0,0)
    ctypes.windll.user32.keybd_event(key,0,2,0)


def open_project(slug:str,action:str)->dict:
    """Open only a named child of RAVEN's dedicated external-project root."""
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,78}[a-z0-9]|[a-z0-9]",slug):raise ValueError("invalid_project_id")
    project=(PROJECTS_ROOT/slug).resolve()
    try:project.relative_to(PROJECTS_ROOT)
    except ValueError:raise ValueError("project_outside_allowlist")
    if not project.is_dir():raise FileNotFoundError("project_folder_not_found")
    if action=="folder":
        subprocess.Popen(["explorer.exe",str(project)],close_fds=True)
        return {"ok":True,"verified":True,"action":action,"project":slug,"state":"folder_dispatched"}
    code=shutil.which("code") or shutil.which("code.cmd")
    if not code:
        candidates=[os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),r"C:\Program Files\Microsoft VS Code\bin\code.cmd"]
        code=next((x for x in candidates if os.path.isfile(x)),"")
    if not code:raise FileNotFoundError("vscode_not_found")
    subprocess.Popen([code,str(project)],close_fds=True)
    return {"ok":True,"verified":True,"action":action,"project":slug,"state":"vscode_dispatched"}


def close_app(app_id:str)->dict:
    """Close only the explicitly allowlisted application's known processes."""
    app=APPS[app_id];names=app.get("processes") or app.get("executables") or []
    if app_id in {"youtube","chatgpt"}:
        return {"ok":False,"verified":False,"app_id":app_id,"label":app["label"],"error":"that target is a browser tab, and closing an arbitrary tab is not safely supported"}
    if app_id=="chrome":
        return {"ok":False,"verified":False,"app_id":app_id,"label":app["label"],"error":"closing Chrome could discard every open browser window; close it directly or add an explicit browser-session controller"}
    if not names or not process_running(names):
        return {"ok":True,"verified":True,"app_id":app_id,"label":app["label"],"method":"process_check","state":"already_closed"}
    if app_id=="steam":
        executable=discover(app)
        if executable:subprocess.run([executable,"-shutdown"],capture_output=True,timeout=8,check=False)
    else:
        # Multi-process desktop clients may briefly respawn a helper after the
        # first termination. Repeat only against the same fixed image names and
        # require consecutive stopped observations before reporting success.
        stable=0
        for _ in range(12):
            if process_running(names):
                stable=0
                for name in names:subprocess.run(["taskkill","/IM",name,"/T","/F"],capture_output=True,text=True,timeout=8,check=False)
            else:
                stable+=1
                if stable>=3:break
            time.sleep(.35)
    closed=not process_running(names)
    return {"ok":closed,"verified":closed,"app_id":app_id,"label":app["label"],"method":"allowlisted_process_close","state":"process_closed" if closed else "close_unverified","error":"the application process is still running" if not closed else ""}


def launch(app_id:str,query:str="",guild_id:str="",channel_id:str="",action:str="")->dict:
    app=APPS[app_id]; executable=discover(app)
    if action=="close":return close_app(app_id)
    if action=="status":
        names=app.get("processes") or app.get("executables") or []
        running=bool(names and process_running(names))
        return {"ok":True,"verified":True,"app_id":app_id,"label":app["label"],"method":"process_check","state":"process_running" if running else "process_stopped","running":running}
    if app_id=="youtube":
        url="https://www.youtube.com/results?search_query="+quote_plus(query[:160]) if query else app["uri"]
        chrome=discover(APPS["chrome"])
        if chrome:
            subprocess.Popen([chrome,url],close_fds=True)
            verified=wait_for_process(["chrome.exe"],5)
            return {"ok":verified,"verified":verified,"app_id":app_id,"label":app["label"],"method":"chrome_allowlisted_url","state":"browser_dispatched" if verified else "launch_unverified","query":query}
        open_registered_target(url)
        return {"ok":True,"verified":False,"app_id":app_id,"label":app["label"],"method":"default_browser_allowlisted_url","state":"browser_dispatched","query":query}
    if app_id=="spotify" and action in {"next","previous"}:
        if not process_running(["Spotify.exe"]):open_registered_target("spotify:");wait_for_process(["Spotify.exe"],8)
        send_media_key(action)
        return {"ok":True,"verified":False,"app_id":app_id,"label":app["label"],"method":"windows_media_key","state":"command_dispatched","action":action}
    if app_id=="spotify" and query:
        open_registered_target("spotify:search:"+quote(query[:160],safe=""))
        verified=wait_for_process(["Spotify.exe"],8)
        return {"ok":verified,"verified":verified,"app_id":app_id,"label":app["label"],"method":"registered_uri_search","state":"search_opened" if verified else "launch_unverified","query":query}
    elif app_id=="discord" and guild_id and channel_id:
        if not re.fullmatch(r"\d{5,24}",guild_id) or not re.fullmatch(r"\d{5,24}",channel_id):
            raise ValueError("invalid_discord_channel_id")
        open_registered_target(f"discord://-/channels/{guild_id}/{channel_id}")
        return {"ok":True,"verified":False,"app_id":app_id,"label":app["label"],"method":"allowlisted_channel_uri","state":"channel_dispatched"}
    elif app_id=="apex":
        if process_running(app["processes"]):return {"ok":True,"verified":True,"app_id":app_id,"label":app["label"],"method":"existing_process","state":"process_verified"}
        steam=discover(APPS["steam"])
        if not steam:return {"ok":False,"verified":False,"app_id":app_id,"label":app["label"],"error":"Steam is not installed or discoverable"}
        subprocess.Popen([steam,"-applaunch",app["steam_app_id"]],close_fds=True)
        verified=wait_for_process(app["processes"],25)
        return {"ok":verified,"verified":verified,"app_id":app_id,"label":app["label"],"method":"steam_applaunch","state":"process_verified" if verified else "launch_unverified","error":"Steam accepted the Apex launch request, but the Apex process did not appear within 25 seconds" if not verified else ""}
    elif executable:
        names=app.get("executables",[])
        existing=bool(names and process_running(names))
        if not existing:subprocess.Popen([executable],close_fds=True)
        verified=wait_for_process(names,5) if names else True
        focused=focus_process(names) if verified and names else False
        if app_id=="spotify" and verified and not focused:
            open_registered_target("spotify:");time.sleep(.7);focused=focus_process(names)
        return {"ok":verified,"verified":verified,"app_id":app_id,"label":app["label"],"method":"existing_process" if existing else "executable","state":"process_verified" if verified else "launch_unverified","focused":focused}
    elif app.get("uri"):
        open_registered_target(app["uri"])
        return {"ok":True,"verified":False,"app_id":app_id,"label":app["label"],"method":"registered_uri","state":"target_dispatched"}
    else:raise FileNotFoundError(f"{app['label']} is not installed or registered")


class Handler(BaseHTTPRequestHandler):
    server_version="RAVENHostBridge/1.0"
    def log_message(self,format,*args):return
    def reply(self,status:int,payload:dict):
        body=json.dumps(payload).encode();self.send_response(status);self.send_header("Content-Type","application/json");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def authorized(self)->bool:
        supplied=self.headers.get("Authorization","").removeprefix("Bearer ")
        return bool(TOKEN) and hmac.compare_digest(supplied,TOKEN)
    def do_GET(self):
        if not self.authorized():return self.reply(401,{"ok":False,"error":"unauthorized"})
        if urlparse(self.path).path!="/health":return self.reply(404,{"ok":False,"error":"not_found"})
        return self.reply(200,{"ok":True,"version":BRIDGE_VERSION,"policy":"fixed_allowlist_no_shell","apps":[{"id":key,"label":value["label"],"installed":bool(discover(value) or value.get("uri") or (value.get("steam_app_id") and discover(APPS["steam"])))} for key,value in APPS.items()]})
    def do_POST(self):
        if not self.authorized():return self.reply(401,{"ok":False,"error":"unauthorized"})
        route=urlparse(self.path).path
        if route not in {"/launch","/project"}:return self.reply(404,{"ok":False,"error":"not_found"})
        try:
            length=min(int(self.headers.get("Content-Length","0")),2048);payload=json.loads(self.rfile.read(length));app_id=str(payload.get("app_id","")).lower()
            if route=="/project":
                action=str(payload.get("action","")).lower();slug=str(payload.get("slug","")).lower()
                if action not in {"folder","vscode"}:return self.reply(400,{"ok":False,"error":"project_action_not_allowlisted"})
                return self.reply(200,open_project(slug,action))
            if app_id not in APPS:return self.reply(400,{"ok":False,"error":"app_not_allowlisted"})
            query=str(payload.get("query","")).strip()
            action=str(payload.get("action","")).strip().lower()
            guild_id=str(payload.get("guild_id","")).strip();channel_id=str(payload.get("channel_id","")).strip()
            if len(query)>160:return self.reply(400,{"ok":False,"error":"query_too_long"})
            if action not in {"","next","previous","close","status"}:return self.reply(400,{"ok":False,"error":"action_not_allowlisted"})
            return self.reply(200,launch(app_id,query,guild_id,channel_id,action))
        except Exception as exc:return self.reply(409,{"ok":False,"error":str(exc)[:180]})


if __name__=="__main__":
    if len(TOKEN)<32:raise SystemExit("Set RAVEN_DESKTOP_BRIDGE_TOKEN to at least 32 random characters")
    print(f"RAVEN desktop bridge listening on {BIND}:{PORT}; fixed allowlist only")
    ThreadingHTTPServer((BIND,PORT),Handler).serve_forever()
