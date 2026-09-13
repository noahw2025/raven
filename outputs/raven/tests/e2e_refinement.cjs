const fs=require('fs');const path=require('path');const assert=require('assert');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
const origin='http://127.0.0.1:8080';let cookie='';
async function call(route,options={}){const response=await fetch(origin+'/api'+route,{...options,headers:{...(options.headers||{}),...(cookie?{Cookie:cookie}:{})}});const set=response.headers.get('set-cookie');if(set)cookie=set.split(';')[0];const body=await response.text();if(!response.ok)throw new Error(`${route} ${response.status}: ${body}`);return body?JSON.parse(body):{}}
const json=(method,body)=>({method,headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
(async()=>{
  await call('/login',json('POST',{password:env.RAVEN_ADMIN_PASSWORD}));
  const dashboard=await call('/dashboard');assert.match(dashboard.voice.tts,/1\.27x/);assert.match(dashboard.voice.turn_detection,/2\.1.*2\.6/);
  const before=(await call('/memories')).length;
  await call('/chat',json('POST',{message:'Could you open Spotify and play something right now?',channel:'text'}));
  await new Promise(resolve=>setTimeout(resolve,900));
  const after=(await call('/memories')).length;assert.equal(after,before,'transient tool request must not become memory');
  const created=await call('/memories',json('POST',{content:'Owner test memory for graph editing',kind:'fact',importance:4,sensitive:false,excluded:false,pinned:false,rationale:'acceptance test'}));
  const graph=await call('/graph');assert(graph.nodes.some(n=>n.id===created.id),'created memory must appear in graph');
  const edited=await call('/memories/'+created.id,json('PUT',{content:'Owner edited memory from graph acceptance test',kind:'correction',importance:5,sensitive:false,excluded:true,pinned:false,rationale:'edited in acceptance test'}));assert.equal(edited.excluded,true);assert.match(edited.content,/edited memory/);
  await call('/memories/'+created.id,{method:'DELETE'});assert(!(await call('/memories')).some(m=>m.id===created.id));
  const html=await (await fetch(origin+'/')).text();assert(html.includes('refine.css'));
  const js=await (await fetch(origin+'/static/app.js')).text();assert(js.includes("['command','Home'"));assert(js.includes('openKnowledgeNode(node)'));
  process.stdout.write(JSON.stringify({passed:true,voice_speed:'1.27x',transient_memory_rejected:true,graph_edit_delete:true,navigation_refined:true}));
})().catch(error=>{console.error(error.stack);process.exit(1)});
