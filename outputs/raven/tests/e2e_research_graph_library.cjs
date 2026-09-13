const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
let cookie='',conversation_id=null;
async function say(message,ui_page='talk'){const response=await fetch('http://127.0.0.1:8080/api/chat',{method:'POST',headers:{Cookie:cookie,Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify({message,conversation_id,channel:'voice',ui_page})});assert(response.ok,`${message}: HTTP ${response.status}`);const result=await response.json();conversation_id=result.conversation_id;return result}
(async()=>{
 const login=await fetch('http://127.0.0.1:8080/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});assert(login.ok);cookie=login.headers.get('set-cookie').split(';')[0];
 let result=await say("Gotcha Raven, let's go to research please.");assert.equal(result.ui_action?.page,'research');
 result=await say('Raven, research history of Mayans for me.','research');assert.equal(result.tool_used,'RAVEN typed background tools');assert.equal(result.background_job_ids.length,1);assert.ok(result.research_project_id);assert.match(result.answer,/Starting now.*visible in Research Lab/i);
 const projectsResponse=await fetch('http://127.0.0.1:8080/api/research/projects',{headers:{Cookie:cookie,Origin:'http://localhost:8080'}});assert(projectsResponse.ok);const projects=await projectsResponse.json();assert(projects.some(project=>project.id===result.research_project_id&&/history of Mayans/i.test(project.objective)),'research project must be visible immediately');
 result=await say("Well, you said you were already doing that, didn't you?",'research');assert.equal(result.tool_used,'RAVEN typed background tools');assert.match(result.answer,/(queued|running|waiting|planning|searching|synthesizing|verifying|completed)/i);
 result=await say('rotate the graph left','graph');assert.equal(result.ui_action?.type,'graph_control');assert.equal(result.ui_action?.direction,'left');
 result=await say('zoom in on the graph','graph');assert.equal(result.ui_action?.type,'graph_zoom');
 result=await say('open Spotify');assert.equal(result.tool_used,'Spotify verified control');
 result=await say('play my liked songs on shuffle');assert.equal(result.tool_used,'Spotify verified control');assert.match(result.answer,/Playing your Liked Songs/i);const likedShuffle=result.answer;
 result=await say('play Loser by Tame Impala from my liked songs');assert.equal(result.tool_used,'Spotify verified control');assert.match(result.answer,/Playing .* from your Liked Songs/i);const likedTrack=result.answer;
 await say('close Spotify');
 console.log(JSON.stringify({passed:true,voice_turns:7,likedShuffle,likedTrack,checks:['research navigation','background execution','anaphoric task status','graph rotation','graph zoom','liked songs shuffle verified','saved-track playback verified']}));
})().catch(error=>{console.error(error.stack||error.message);process.exit(1)});
