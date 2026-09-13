const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
const origin='http://127.0.0.1:8080/api';
let cookie='';
async function post(path,body){
  const response=await fetch(origin+path,{method:'POST',headers:{Origin:'http://localhost:8080','Content-Type':'application/json',Cookie:cookie},body:JSON.stringify(body)});
  const setCookie=response.headers.get('set-cookie');if(setCookie)cookie=setCookie.split(';')[0];
  assert(response.ok,`${path}: HTTP ${response.status}`);return response.json();
}
(async()=>{
  await post('/login',{password:env.RAVEN_ADMIN_PASSWORD});
  const low=await post('/chat',{message:'Open the knowledge graph',channel:'voice',ui_page:'talk',voice_confidence:.31,voice_no_speech_probability:.04,voice_stt_model:'large-v3-turbo'});
  assert.equal(low.tool_used,'RAVEN command safety guard');assert.equal(low.ui_action,null);assert.match(low.answer,/repeat/i);
  const high=await post('/chat',{conversation_id:low.conversation_id,message:'Open the knowledge graph',channel:'voice',ui_page:'talk',voice_confidence:.91,voice_no_speech_probability:.01,voice_stt_model:'large-v3-turbo'});
  assert.equal(high.tool_used,'RAVEN interface control');assert.equal(high.ui_action.page,'graph');
  console.log('voice confidence guard: low-confidence action blocked; high-confidence action executed');
})().catch(error=>{console.error(error);process.exit(1)});
