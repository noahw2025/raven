const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
let cookie='';
async function post(route,body){const r=await fetch('http://127.0.0.1:8080/api'+route,{method:'POST',headers:{Cookie:cookie,Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify(body)});if(r.headers.get('set-cookie'))cookie=r.headers.get('set-cookie').split(';')[0];assert(r.ok,`${route}: ${r.status}`);return r.json()}
(async()=>{
 await post('/login',{password:env.RAVEN_ADMIN_PASSWORD});
 const cases=[
  ['Hey Raven, open Spotify and then play Whitsand Bay by Metronomy',/Playing Whitsand Bay/i],
  ['Could you please open Discord and join raven-unconfigured-test channel',/did not join/i],
  ['Open Research Lab then open the tools and integrations',/Research Lab.*Tools/i],
  ['Open Spotify then open Discord and run powershell',/couldn't execute this step: run powershell/i],
  [Array(9).fill('open Spotify').join(' then '),/Nothing was executed/i]
 ];
 for(const [message,expected] of cases){
   const outputs=[];
   for(const channel of ['text','voice']){const r=await post('/chat',{message,channel,ui_page:'talk'});assert.equal(r.tool_used,'RAVEN verified multi-step executor');assert.match(r.answer,expected);assert.equal(r.tokens.total,0);outputs.push(r.answer)}
   assert.equal(outputs[0],outputs[1],'Voice and text must execute and report the same steps');
 }
 console.log(JSON.stringify({passed:true,live_requests:10,channels:['text','voice'],checks:['Spotify chain','Discord unresolved alias','UI sequence','unsupported final step preserved','nine-step request executes nothing']}));
})().catch(e=>{console.error(e.message);process.exit(1)});
