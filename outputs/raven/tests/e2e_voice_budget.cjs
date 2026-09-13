const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
let cookie='',conversation_id=null;
async function say(message){const started=Date.now();const response=await fetch('http://127.0.0.1:8080/api/chat',{method:'POST',headers:{Cookie:cookie,Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify({message,conversation_id,channel:'voice',ui_page:'talk'})});assert(response.ok,`${message}: HTTP ${response.status}`);const result=await response.json();conversation_id=result.conversation_id;return{...result,wall_ms:Date.now()-started}}
(async()=>{
 const login=await fetch('http://127.0.0.1:8080/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});assert(login.ok);cookie=login.headers.get('set-cookie').split(';')[0];
 for(const line of ['I want to plan a useful personal assistant.','It should help with my daily work.','Clear and concise answers matter to me.','It should remember only important preferences.'])await say(line);
 const measured=await say('What should we prioritize first?');
 assert(measured.tokens.total>0,'This must measure a real model turn');
 assert(measured.tokens.total<1800,`Voice prompt used ${measured.tokens.total} tokens`);
 assert(measured.wall_ms<12000,`Voice model took ${measured.wall_ms}ms`);
 assert(measured.answer.split(/\s+/).length<=44,'Voice answer exceeded the spoken limit');
 console.log(JSON.stringify({passed:true,total_tokens:measured.tokens.total,input_tokens:measured.tokens.in,output_tokens:measured.tokens.out,model_ms:measured.timings.model_ms,wall_ms:measured.wall_ms,answer:measured.answer}));
})().catch(error=>{console.error(error.message);process.exit(1)});
