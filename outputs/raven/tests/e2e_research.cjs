const fs=require('fs');
const path=require('path');
const assert=require('assert');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
const origin='http://127.0.0.1:8080';let cookie='';
async function request(route,options={}){
  const response=await fetch(origin+route,{...options,headers:{...(options.headers||{}),...(cookie?{Cookie:cookie}:{})}});
  const setCookie=response.headers.get('set-cookie');if(setCookie)cookie=setCookie.split(';')[0];
  const body=await response.text();if(!response.ok)throw new Error(`${route} returned ${response.status}: ${body}`);return JSON.parse(body);
}
(async()=>{
  await request('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});
  const project=process.env.RAVEN_RESEARCH_PROJECT_ID
    ? {id:process.env.RAVEN_RESEARCH_PROJECT_ID}
    : await request('/api/research/projects',{method:'POST',headers:{Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify({title:'Instagram publishing architecture acceptance test',objective:'Research current official Instagram API content publishing requirements in 2026, including account eligibility, supported media, authentication and permissions, publishing limits, common failure modes, and a recommended implementation architecture',depth:2})});
  let detail;const deadline=Date.now()+600000;
  while(Date.now()<deadline){
    detail=await request('/api/research/projects/'+project.id);
    if(['completed','failed'].includes(detail.project.status))break;
    await new Promise(resolve=>setTimeout(resolve,2000));
  }
  assert(detail);assert.equal(detail.project.status,'completed',detail.project.error||'research timed out');
  assert(detail.sources.length>=8,`only ${detail.sources.length} sources`);assert(detail.findings.length>=5);assert(detail.project.report.length>1600);assert.match(detail.project.report,/\[S\d+\]/);
  assert(/Executive|Answer|Overview/i.test(detail.project.report));assert(/Key findings/i.test(detail.project.report));assert(/Risk|Limitation|Unknown/i.test(detail.project.report));
  assert(!/extractive fallback|follow the \[S#\] links|source snippets/i.test(detail.project.report));
  assert(new Set([...detail.project.report.matchAll(/\[S(\d+)\]/g)].map(x=>x[1])).size>=4,'insufficient citation diversity');
  assert.equal(detail.project.answer_quality,'audited');assert(detail.project.provider);assert(detail.project.model);assert(Number(detail.project.cost_usd)<=0.25);
  assert(detail.project.input_tokens+detail.project.output_tokens>0,'synthesis did not run');
  assert(detail.sources.every(source=>['institutional_primary','research_primary','technical_primary','official_candidate','reputable_secondary','web_source'].includes(source.quality)));
  const followup=await request('/api/chat',{method:'POST',headers:{Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify({message:'Based on the research report you just completed, summarize the account eligibility and publishing limitations. Do not search again.',channel:'text',ui_page:'research'})});
  assert(followup.answer.length>200,followup.answer);assert.equal(followup.tool_used,'RAVEN research knowledge base');assert(!/I don.t have|cannot access|list of links/i.test(followup.answer));
  process.stdout.write(JSON.stringify({passed:true,project_id:project.id,sources:detail.sources.length,findings:detail.findings.length,provider:detail.project.provider,model:detail.project.model,cost_usd:detail.project.cost_usd,input_tokens:detail.project.input_tokens,output_tokens:detail.project.output_tokens,followup_chars:followup.answer.length,quality_tiers:[...new Set(detail.sources.map(source=>source.quality))]}));
})().catch(error=>{console.error(error.stack);process.exit(1)});
