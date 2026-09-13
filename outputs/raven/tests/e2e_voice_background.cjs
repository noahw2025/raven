const assert=require('node:assert/strict');
// Run after e2e_background_tools. No real microphone or external writes.
async function request(route,body){const form=body instanceof FormData;const r=await fetch('http://localhost:8080/api'+route,{method:body?'POST':'GET',headers:{Origin:'http://localhost:8080',...(!form?{'Content-Type':'application/json'}:{})},body:body?(form?body:JSON.stringify(body)):undefined});assert(r.ok,route+': '+r.status);return r}
(async()=>{
 const {jobs}=await (await request('/assistant/jobs')).json();
 const job=jobs.find(j=>j.action==='content'&&j.payload.query.includes('RAVEN integration test')&&j.status==='completed');
 assert(job,'Run background-tool smoke test first');
 const audio=await request('/local-voice/synthesize',{content:'What did my content task produce?'});
 const form=new FormData();form.append('file',await audio.blob(),'voice-command.wav');
 const transcript=await (await request('/local-voice/transcribe',form)).json();
 const result=await (await request('/chat',{conversation_id:job.conversation_id,channel:'voice',message:transcript.text})).json();
 assert.equal(result.tool_used,'RAVEN typed background tools');
 assert.match(result.answer,/garden|gardening/i);
 const speech=await request('/local-voice/synthesize',{content:result.answer});
 assert((await speech.arrayBuffer()).byteLength>1000);
 console.log(JSON.stringify({passed:true,scope:'Synthetic speech -> real local STT -> saved task results -> local TTS (not physical microphone)',transcript:transcript.text,answer:result.answer}));
})().catch(e=>{console.error(e.message);process.exitCode=1});
