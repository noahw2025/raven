const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const gate=require('../app/static/voice_logic.js');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return [x.slice(0,i),x.slice(i+1)]}));
let cookie='';
async function request(route,body){
  const form=body instanceof FormData;
  const res=await fetch('http://127.0.0.1:8080/api'+route,{method:'POST',headers:{Cookie:cookie,Origin:'http://localhost:8080',...(!form?{'Content-Type':'application/json'}:{})},body:form?body:JSON.stringify(body)});
  if(res.headers.get('set-cookie'))cookie=res.headers.get('set-cookie').split(';')[0];
  assert(res.ok,`${route}: HTTP ${res.status}`);return res;
}
(async()=>{
  await request('/login',{password:env.RAVEN_ADMIN_PASSWORD});
  const utterance=await request('/local-voice/synthesize',{content:'Open Spotify and then play Good Morning by Kanye West.'});
  const form=new FormData();form.append('file',await utterance.blob(),'command.wav');
  const transcript=await (await request('/local-voice/transcribe',form)).json();
  assert(gate.isSpeechTurn({activeFrames:60,speechMs:1500,confidence:transcript.confidence,noSpeechProbability:transcript.no_speech_probability,text:transcript.text}));
  const result=await (await request('/chat',{message:transcript.text,channel:'voice',ui_page:'talk'})).json();
  assert.equal(result.tool_used,'RAVEN verified multi-step executor');assert.match(result.answer,/Playing Good Morning/i);
  assert.match(result.answer,/Spotify is open|open command to Spotify/i);assert.doesNotMatch(result.answer,/unreachable|couldn't|Nothing was launched/i);
  const spoken=await request('/local-voice/synthesize',{content:result.answer});assert((await spoken.arrayBuffer()).byteLength>1000);
  const current=await (await request('/chat',{message:'What is playing on Spotify?',channel:'voice',conversation_id:result.conversation_id})).json();
  assert.match(current.answer,/Good Morning.*Kanye West.*is playing/i);
  const paused=await (await request('/chat',{message:'Hey Raven pause Spotify music',channel:'voice',conversation_id:result.conversation_id})).json();
  assert.equal(paused.tool_used,'Spotify verified control');assert.match(paused.answer,/confirmed.*paused/i);
  const pausedState=await (await request('/chat',{message:'What is playing on Spotify?',channel:'voice',conversation_id:result.conversation_id})).json();
  assert.match(pausedState.answer,/Good Morning.*Kanye West.*paused/i);
  const resumed=await (await request('/chat',{message:'Resume the music',channel:'voice',conversation_id:result.conversation_id})).json();
  assert.match(resumed.answer,/confirmed.*resumed/i);
  const skipped=await (await request('/chat',{message:'Skip the song.',channel:'voice',conversation_id:result.conversation_id})).json();
  assert.equal(skipped.tool_used,'Spotify verified control');assert.match(skipped.answer,/confirmed.*skipped/i);
  const skippedState=await (await request('/chat',{message:'What is playing on Spotify?',channel:'voice',conversation_id:result.conversation_id})).json();
  assert.doesNotMatch(skippedState.answer,/Good Morning by Kanye West/i);
  const cleanup=await (await request('/chat',{message:'Pause Spotify music',channel:'voice',conversation_id:result.conversation_id})).json();
  assert.match(cleanup.answer,/confirmed.*paused/i);
  console.log(JSON.stringify({passed:true,scope:'Synthetic audio -> actual STT -> voice chat -> Spotify playback/readback -> verified pause/resume/skip -> final paused state -> TTS; not physical microphone testing',transcript:transcript.text,answer:result.answer,readback:current.answer,pause:paused.answer,paused_state:pausedState.answer,resume:resumed.answer,skip:skipped.answer,skipped_state:skippedState.answer,cleanup:cleanup.answer,execution_ms:result.latency_ms}));
})().catch(e=>{console.error(e.message);process.exit(1)});
