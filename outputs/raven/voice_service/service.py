import os
import io
import json
import asyncio
import tempfile
import time
import math
import re
from threading import Lock
from difflib import SequenceMatcher
from pathlib import Path
from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from pydantic import BaseModel, Field
from faster_whisper import WhisperModel
from kokoro_onnx import Kokoro
import soundfile as sf
import numpy as np
from phonemizer.backend.espeak.wrapper import EspeakWrapper
from parakeet_stream import ParakeetRealtime
from silero_vad import load_silero_vad

Path(os.environ.get("TMPDIR","/models/runtime-tmp")).mkdir(parents=True,exist_ok=True)
EspeakWrapper.set_library("/lib/x86_64-linux-gnu/libespeak-ng.so.1")

app=FastAPI(title="RAVEN Local Voice",docs_url=None,redoc_url=None)
model=None
model_info={"status":"cold"}
tts_model=None
tts_lock=Lock()
stream_model=None
stream_model_info={"status":"cold","engine":"parakeet-realtime-eou"}
stream_lock=Lock()
vad_model=None

COMMAND_VOCABULARY=(
    "RAVEN voice commands. ARISE. Open Spotify. Close Spotify. Pause Spotify. "
    "Resume Spotify. Skip the song. Previous song. Play my liked songs. "
    "Shuffle my liked songs. Open Steam. Open Discord. Open YouTube. "
    "Open Research Lab. Open Career Center. Open Knowledge Graph. "
    "Start deep research."
)

def whisper():
    global model,model_info
    if model is None:
        primary=os.environ.get("STT_PRIMARY_MODEL","large-v3-turbo")
        device=os.environ.get("STT_DEVICE","cuda")
        compute=os.environ.get("STT_COMPUTE_TYPE","float16")
        try:
            model=WhisperModel(primary,device=device,compute_type=compute,download_root="/models/huggingface")
            model_info={"status":"ready","engine":"faster-whisper","model":primary,"device":device,"compute_type":compute,"fallback":False}
        except Exception as error:
            fallback=os.environ.get("STT_FALLBACK_MODEL","base.en")
            model=WhisperModel(fallback,device="cpu",compute_type="int8",download_root="/models/huggingface")
            model_info={"status":"degraded","engine":"faster-whisper","model":fallback,"device":"cpu","compute_type":"int8","fallback":True,"fallback_reason":type(error).__name__}
    return model

def kokoro():
    global tts_model
    if tts_model is None:tts_model=Kokoro("/opt/kokoro/kokoro-v1.0.onnx","/opt/kokoro/voices-v1.0.bin")
    return tts_model

def parakeet():
    global stream_model,stream_model_info
    if stream_model is None:
        name=os.environ.get("PARAKEET_MODEL","nvidia/parakeet_realtime_eou_120m-v1")
        try:
            stream_model=ParakeetRealtime(name,os.environ.get("PARAKEET_DEVICE","cuda"))
            stream_model_info={"status":"ready","engine":"parakeet-realtime-eou","model":name,"device":os.environ.get("PARAKEET_DEVICE","cuda"),"frame_ms":16,"decode_chunk_ms":80,"eou":True}
        except Exception as error:
            stream_model_info={"status":"unavailable","engine":"parakeet-realtime-eou","model":name,"error":type(error).__name__}
            raise
    return stream_model

def silero():
    global vad_model
    if vad_model is None:vad_model=load_silero_vad(onnx=True)
    return vad_model

@app.get("/health")
def health():return {"status":"ok" if model_info.get("status") in {"ready","degraded"} else "warming","streaming_stt":stream_model_info,"verification_stt":model_info,"vad":{"status":"ready" if vad_model is not None else "cold","engine":"silero-vad-v6.2"},"tts":"kokoro-82m/af_heart","local":True,"audio_retained":False}

@app.on_event("startup")
def warm_models():
    whisper()
    parakeet();silero()
    with tts_lock:kokoro().create("Ready.",voice="af_heart",speed=1.27,lang="en-us")

ACTION_TERMS=re.compile(r"\b(open|close|play|pause|resume|skip|previous|volume|shuffle|research|apply|delete|send|post|publish|create|go to|show|zoom|spotify|discord|youtube|steam)\b",re.I)

def verify_streamed(audio:bytearray,primary:str,eou_probability:float|None,force=False):
    """Use Whisper Turbo only when an action/name is risky or Parakeet is unsure."""
    consequential=re.search(r"\b(apply|delete|send|post|publish|purchase|trade|transfer)\b",primary,re.I)
    suspicious=re.search(r"\b(?:tayman|paula|can i west|canye|spot of i|you tube)\b",primary,re.I)
    # Routine reversible commands stay on the fast Parakeet path. Whisper is
    # reserved for VAD fallbacks, suspicious entities, and consequential acts.
    should_verify=force or not primary or consequential or suspicious or (eou_probability or 0)<.55
    if not should_verify:return primary,round(max(.58,eou_probability or .68),4),False,"parakeet"
    signal=np.frombuffer(bytes(audio),dtype=np.int16).astype(np.float32)/32768.0
    segments,_=whisper().transcribe(signal,language="en",vad_filter=True,beam_size=3,condition_on_previous_text=False,initial_prompt=COMMAND_VOCABULARY,hotwords="ARISE Raven Spotify YouTube Discord Steam Apex Legends ChatGPT research career knowledge pause resume skip shuffle")
    rows=list(segments);alternate=" ".join(row.text.strip() for row in rows).strip()
    alternate_conf=sum(math.exp(min(0,float(row.avg_logprob))) for row in rows)/len(rows) if rows else 0
    agreement=SequenceMatcher(None,primary.lower(),alternate.lower()).ratio() if primary and alternate else 0
    if alternate and (not primary or (alternate_conf>=.62 and agreement<.72)):
        return alternate,round(min(.98,max(alternate_conf,.58)),4),True,"whisper-turbo"
    confidence=min(.99,max(.52,(eou_probability or .55)*.55+agreement*.45))
    return primary or alternate,round(confidence,4),True,"parakeet+whisper-turbo"

stream_session_lock=asyncio.Lock()

@app.websocket("/stream")
async def stream(websocket:WebSocket):
    origin=websocket.headers.get("origin","")
    if origin not in {"http://localhost:8080","http://127.0.0.1:8080"}:
        await websocket.close(code=1008);return
    await websocket.accept()
    if stream_session_lock.locked():
        await websocket.send_json({"type":"error","message":"Another RAVEN tab has the voice channel open. End that session before starting this one."})
        await websocket.close(code=1013);return
    await stream_session_lock.acquire()
    try:
        engine=parakeet();vad=silero()
    except Exception:
        stream_session_lock.release()
        await websocket.send_json({"type":"error","message":"Parakeet streaming model is unavailable","streaming_stt":stream_model_info});await websocket.close(code=1011);return
    pcm=bytearray();decode_buffer=bytearray();vad_buffer=bytearray();latest="";speech=False;silence_ms=0;started=time.perf_counter();turn_started=None
    with stream_lock:
        engine.reset();vad.reset_states()
    await websocket.send_json({"type":"ready","pipeline":{"vad":"silero-vad-v6.2","stt":stream_model_info,"verifier":model_info,"sample_rate":16000,"format":"pcm_s16le"}})
    try:
        while True:
            packet=await websocket.receive()
            if packet.get("type")=="websocket.disconnect":break
            if packet.get("text"):
                control=json.loads(packet["text"])
                if control.get("type")=="reset":
                    with stream_lock:engine.reset();vad.reset_states()
                    pcm.clear();decode_buffer.clear();vad_buffer.clear();latest="";speech=False;silence_ms=0
                continue
            chunk=packet.get("bytes") or b""
            if not chunk:continue
            pcm.extend(chunk);decode_buffer.extend(chunk);vad_buffer.extend(chunk)
            # Keep only pre-roll while idle, not minutes of silence for verification.
            if not speech and len(pcm)>16000:del pcm[:-16000]
            while len(vad_buffer)>=1024:
                window=bytes(vad_buffer[:1024]);del vad_buffer[:1024]
                probability=float(vad(__import__('torch').from_numpy(np.frombuffer(window,dtype=np.int16).astype(np.float32)/32768.0),16000).item())
                if probability>=.5:
                    if not speech:turn_started=time.perf_counter();await websocket.send_json({"type":"speech_started"})
                    speech=True;silence_ms=0
                elif speech: silence_ms+=32
            while len(decode_buffer)>=2560:
                frame=bytes(decode_buffer[:2560]);del decode_buffer[:2560]
                with stream_lock:result=await asyncio.to_thread(engine.push,frame)
                if result.text and result.text!=latest:
                    if not speech:
                        speech=True;turn_started=time.perf_counter();silence_ms=0
                        await websocket.send_json({"type":"speech_started"})
                    latest=result.text;await websocket.send_json({"type":"partial","text":latest,"processing_ms":round(result.processing_ms,1)})
                if result.final:
                    final,confidence,verified,selected=await asyncio.to_thread(verify_streamed,pcm,latest,result.eou_probability,False)
                    await websocket.send_json({"type":"final","text":final,"confidence":confidence,"verified":verified,"selected_by":selected,"eou_probability":result.eou_probability,"turn_ms":round((time.perf_counter()-(turn_started or started))*1000),"stt":stream_model_info})
                    pcm.clear();decode_buffer.clear();vad_buffer.clear();latest="";speech=False;silence_ms=0;turn_started=None;vad.reset_states()
            incomplete=bool(re.search(r"\b(?:and|or|the|on|to|for|by|go ahead|make it)\s*$",latest,re.I))
            if speech and silence_ms>=(1800 if incomplete else 1100) and (latest or len(pcm)>=6400):
                with stream_lock:engine.reset()
                final,confidence,verified,selected=await asyncio.to_thread(verify_streamed,pcm,latest,None,True)
                await websocket.send_json({"type":"final","text":final,"confidence":confidence,"verified":verified,"selected_by":selected,"eou_probability":None,"vad_fallback":True,"turn_ms":round((time.perf_counter()-(turn_started or started))*1000),"stt":stream_model_info})
                pcm.clear();decode_buffer.clear();vad_buffer.clear();latest="";speech=False;silence_ms=0;turn_started=None;vad.reset_states()
    except WebSocketDisconnect:pass
    finally:
        with stream_lock:engine.reset();vad.reset_states()
        stream_session_lock.release()

@app.post("/transcribe")
async def transcribe(file:UploadFile=File(...)):
    started=time.perf_counter()
    raw=await file.read()
    if not raw or len(raw)>15_000_000:raise HTTPException(400,"Invalid local audio buffer")
    suffix=Path(file.filename or "speech.webm").suffix or ".webm"
    with tempfile.NamedTemporaryFile(suffix=suffix,delete=False,dir=os.environ.get("TMPDIR","/tmp")) as handle:handle.write(raw);path=handle.name
    try:
        segments,info=whisper().transcribe(
            path,language="en",vad_filter=True,beam_size=3,
            condition_on_previous_text=False,
            initial_prompt=COMMAND_VOCABULARY,
            hotwords="ARISE Raven Spotify YouTube Discord Steam research career knowledge pause resume skip shuffle",
            vad_parameters={"min_silence_duration_ms":650,"speech_pad_ms":240},
        )
        rows=list(segments);text=" ".join(segment.text.strip() for segment in rows).strip()
        confidence=sum(math.exp(min(0,float(segment.avg_logprob))) for segment in rows)/len(rows) if rows else 0.0
        no_speech=max((float(segment.no_speech_prob) for segment in rows),default=1.0)
        wake_text=bool(__import__('re').search(r"\barise\b",text,__import__('re').I))
        wake_detected=bool(wake_text and confidence>=.45 and no_speech<=.65 and info.duration>=.30)
        return {"text":text,"language":info.language,"duration":info.duration,"confidence":round(confidence,4),"no_speech_probability":round(no_speech,4),"processing_ms":round((time.perf_counter()-started)*1000),"wake_phrase_detected":wake_detected,"stt":model_info}
    finally:
        os.unlink(path)

class Speech(BaseModel):text:str=Field(min_length=1,max_length=6000)

@app.post("/synthesize")
def synthesize(data:Speech):
    started=time.perf_counter()
    # Exactly 20% faster than the previous 1.06 setting. Cap the long quiet
    # tail Kokoro can add at punctuation so sentence chunks join naturally.
    with tts_lock:samples,rate=kokoro().create(data.text,voice="af_heart",speed=1.27,lang="en-us")
    signal=np.asarray(samples)
    if signal.size:
        amplitude=np.max(np.abs(signal),axis=1) if signal.ndim>1 else np.abs(signal)
        voiced=np.flatnonzero(amplitude>0.004)
        if voiced.size:
            samples=signal[:min(signal.shape[0],int(voiced[-1])+1+int(rate*.07))]
    output=io.BytesIO();sf.write(output,samples,rate,format="WAV",subtype="PCM_16")
    elapsed=(time.perf_counter()-started)*1000
    return Response(output.getvalue(),media_type="audio/wav",headers={"Cache-Control":"no-store","X-Raven-TTS-Ms":f"{elapsed:.0f}","X-Raven-Voice":"kokoro-af-heart","X-Raven-Voice-Speed":"1.27","X-Raven-Tail-Silence-Ms":"70"})
