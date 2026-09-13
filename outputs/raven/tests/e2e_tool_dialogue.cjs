const fs=require('fs');const path=require('path');const assert=require('assert');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
const origin='http://localhost:8080';let cookie='',conversation_id=null;
async function request(route,options={}){const response=await fetch(origin+route,{...options,headers:{...(options.headers||{}),...(cookie?{Cookie:cookie}:{})}});const setCookie=response.headers.get('set-cookie');if(setCookie)cookie=setCookie.split(';')[0];const body=await response.text();if(!response.ok)throw new Error(`${route} ${response.status}: ${body}`);return JSON.parse(body)}
async function say(message){const result=await request('/api/chat',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({message,conversation_id,channel:'text',ui_page:'talk'})});conversation_id=result.conversation_id;return result}
(async()=>{
  await request('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});
  let r=await say('what can you do');assert.equal(r.tool_used,'RAVEN capability registry');assert(!/cannot access external data|cannot access the internet/i.test(r.answer));
  r=await say('what is career centers');assert.equal(r.tool_used,'Career capability registry');assert(/full job workflow/i.test(r.answer));
  r=await say('you will be able to apply for jobs for me right');assert.equal(r.tool_used,'Career capability registry');assert(/targeted resume/i.test(r.answer));
  r=await say('can you do deep research through the web for me through the deep research agent part');assert.equal(r.tool_used,'RAVEN Deep Research capability');assert.equal(r.research_project_id,null);
  r=await say('Do deep research on the history of cats');assert(r.research_project_id);assert(/history of cats/i.test(r.answer));
  r=await say('what is it');assert.equal(r.tool_used,'RAVEN Deep Research');assert(/history of cats/i.test(r.answer));
  r=await say('tell me what we find on the history of cats');assert.equal(r.tool_used,'RAVEN Deep Research');assert(/currently|completed/i.test(r.answer));assert(!/7500 BCE/i.test(r.answer));
  r=await say('open youtube');assert.equal(r.tool_used,'YouTube verified browser control');assert.equal(r.ui_action,null);assert(/opened YouTube in Chrome/i.test(r.answer));
  r=await say('can you open steam');assert.equal(r.tool_used,'RAVEN capability registry');assert(/allowlist|companion/i.test(r.answer));
  r=await say('can you post to instagram');assert.equal(r.tool_used,'RAVEN capability registry');assert(/status is/i.test(r.answer));
  r=await say('what is career centers');r=await say('is that from the deep research agent though?');assert.equal(r.tool_used,'RAVEN provenance ledger');assert(/^No\./.test(r.answer));
  r=await say('open steam');assert.equal(r.tool_used,'Allowlisted Windows companion');assert(/Steam is open/i.test(r.answer));
  process.stdout.write(JSON.stringify({passed:true,conversation_id,steam:r.answer,youtube:true,research_context:true,capability_truth:true}));
})().catch(error=>{console.error(error.stack);process.exit(1)});
