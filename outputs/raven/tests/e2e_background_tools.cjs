// Real service smoke test: saves labeled research/content and a job search.
// Does not submit applications, publish content, or control desktop apps.
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
let cookie='';
async function api(route,body){const r=await fetch('http://127.0.0.1:8080/api'+route,{method:body?'POST':'GET',headers:{Cookie:cookie,Origin:'http://localhost:8080','Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});if(r.headers.get('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];assert(r.ok,route+': '+r.status);return r.json()}
(async()=>{
 await api('/login',{password:env.RAVEN_ADMIN_PASSWORD});
 const text=await api('/chat',{channel:'text',message:'Find sales jobs in Atlanta in the background'});
 assert.equal(text.tool_used,'RAVEN typed background tools');
 const cid=text.conversation_id;
 const voice=await api('/chat',{conversation_id:cid,channel:'voice',message:'Find sales jobs in Atlanta in the background'});
 assert.equal(voice.tool_used,text.tool_used);
 let {jobs}=await api('/assistant/jobs?conversation_id='+cid);
 assert.equal(jobs.filter(j=>j.action==='career_search').length,1,'Active duplicate should reuse task');
 const status=await api('/chat',{conversation_id:cid,channel:'voice',message:'What did my job search find?'});
 assert.equal(status.tool_used,'RAVEN typed background tools');
 const chain=await api('/chat',{conversation_id:cid,channel:'voice',message:'Research the history of domestic cats for a RAVEN integration test then create a content campaign about RAVEN integration test garden tips for Instagram'});
 assert.equal(chain.tool_used,'RAVEN verified multi-step executor');
 const unknown=await api('/chat',{conversation_id:cid,channel:'voice',message:'Apply for job raven-nonexistent-test-job'});
 assert.match(unknown.answer,/unique exact|saved ID/i);
 const end=Date.now()+240000;
 while(Date.now()<end){
   ({jobs}=await api('/assistant/jobs?conversation_id='+cid));
   if(jobs.length===3&&jobs.every(j=>['completed','failed'].includes(j.status)))break;
   await new Promise(r=>setTimeout(r,4000));
 }
 console.log(JSON.stringify({conversation_id:cid,tasks:jobs.map(j=>({id:j.id,action:j.action,status:j.status,summary:j.result?.summary,job_count:j.result?.jobs?.length,post_count:j.result?.posts?.length})),routing_checks_passed:true}));
 assert(jobs.some(j=>j.action==='career_search'&&j.status==='completed'),'Real career search did not finish');
 assert(jobs.some(j=>j.action==='content'&&j.status==='completed'),'Real content drafts did not finish');
 const answer=await api('/chat',{conversation_id:cid,channel:'voice',message:'What did my content task produce?'});
 assert.equal(answer.tool_used,'RAVEN typed background tools');
 const after=await api('/assistant/jobs?conversation_id='+cid);assert.equal(after.jobs.length,jobs.length,'Follow-up must not start new work');
 console.log(JSON.stringify({saved_result_followup:true,answer:answer.answer}));
})().catch(e=>{console.error(e.message);process.exitCode=1});
