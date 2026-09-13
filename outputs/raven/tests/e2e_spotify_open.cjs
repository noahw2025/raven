const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
let cookie='';
async function post(route,body){
  const response=await fetch('http://127.0.0.1:8080/api'+route,{method:'POST',headers:{Cookie:cookie,Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify(body)});
  if(response.headers.get('set-cookie'))cookie=response.headers.get('set-cookie').split(';')[0];
  assert(response.ok,`${route}: HTTP ${response.status}`);return response.json();
}
(async()=>{
  await post('/login',{password:env.RAVEN_ADMIN_PASSWORD});
  for(const channel of ['text','voice']){
    const result=await post('/chat',{message:'Hey Raven, can you open Spotify?',channel,ui_page:'talk'});
    assert.equal(result.tool_used,'Spotify verified control');
    assert.match(result.answer,/Spotify is open/i);
    assert.doesNotMatch(result.answer,/keyless|OAuth|current status|capability/i);
    assert.equal(result.tokens.total,0);
  }
  const closed=await post('/chat',{message:'close fight if I',channel:'voice',ui_page:'talk'});
  assert.equal(closed.tool_used,'Allowlisted Windows companion');
  assert.match(closed.answer,/Spotify is closed/i);
  assert.equal(closed.tokens.total,0);
  console.log(JSON.stringify({passed:true,commands:['Hey Raven, can you open Spotify?','close fight if I (observed voice transcript)'],channels:['text','voice'],result:'Spotify process verified open and closed'}));
})().catch(error=>{console.error(error.message);process.exit(1)});
