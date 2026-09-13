const fs=require('fs');
const path=require('path');
const assert=require('assert');

const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
const origin='http://localhost:8080';
let cookie='';
async function raw(route,options={}){
  const response=await fetch(origin+route,{...options,headers:{...(options.headers||{}),...(cookie?{Cookie:cookie}:{})}});
  const setCookie=response.headers.get('set-cookie');if(setCookie)cookie=setCookie.split(';')[0];
  return response;
}
async function json(route,options={}){
  const response=await raw(route,options);const body=await response.text();
  if(!response.ok)throw new Error(`${route} returned ${response.status}: ${body}`);
  return JSON.parse(body);
}

(async()=>{
  await json('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});
  const home=await raw('/');
  assert.equal(home.status,200);
  assert.equal(home.headers.get('x-content-type-options'),'nosniff');
  assert.equal(home.headers.get('x-frame-options'),'DENY');
  assert.match(home.headers.get('content-security-policy')||'',/frame-ancestors 'none'/);
  assert.match(home.headers.get('permissions-policy')||'',/microphone=\(self\)/);

  const crossOrigin=await raw('/api/tasks',{method:'POST',headers:{Origin:'https://attacker.invalid','Content-Type':'application/json'},body:JSON.stringify({title:'must not be created'})});
  assert.equal(crossOrigin.status,403);
  const traversal=await raw('/static/../.env');assert.notEqual(traversal.status,200);

  const tools=await json('/api/tools');const serialized=JSON.stringify(tools).toLowerCase();
  for(const marker of ['access_token','api_key','client_secret','private_key'])assert(!serialized.includes(marker));
  assert(tools.some(x=>x.id==='deep_research'&&x.status==='ready'));
  assert(tools.some(x=>x.id==='local_voice'&&x.status==='ready'));

  const command=await json('/api/chat',{method:'POST',headers:{Origin:origin,'Content-Type':'application/json'},body:JSON.stringify({message:'Raven, start a general mission to inspect local product readiness',channel:'voice'})});
  assert.equal(command.tool_used,'RAVEN mission orchestrator');assert(command.mission_run_id);assert.equal(command.ui_action.page,'missions');
  const run=await json('/api/runs/'+command.mission_run_id);assert.equal(run.run.template,'general');assert(run.steps.length>0);
  await json('/api/runs/'+command.mission_run_id+'/cancel',{method:'POST',headers:{Origin:origin}});

  process.stdout.write(JSON.stringify({passed:true,security_headers:true,cross_origin_guard:true,path_traversal_guard:true,secret_free_tool_api:true,voice_agent_command:true,mission_id:command.mission_run_id}));
})().catch(error=>{console.error(error.stack);process.exit(1)});
