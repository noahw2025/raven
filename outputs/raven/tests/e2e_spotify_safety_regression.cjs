const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
let cookie='',conversation_id=null;
async function say(message){const response=await fetch('http://127.0.0.1:8080/api/chat',{method:'POST',headers:{Cookie:cookie,Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify({message,conversation_id,channel:'voice',ui_page:'talk'})});assert(response.ok,`${message}: HTTP ${response.status}`);const result=await response.json();conversation_id=result.conversation_id;return result}
(async()=>{
 const login=await fetch('http://127.0.0.1:8080/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});assert(login.ok);cookie=login.headers.get('set-cookie').split(';')[0];
 const opened=await say('Yeah, I want to listen to music. Can you open Spotify, please?');assert.equal(opened.tool_used,'Spotify verified control');assert.match(opened.answer,/Spotify is open/i);
 const play=await say('Play');assert.equal(play.tool_used,'Spotify verified control');assert.doesNotMatch(play.answer,/qwen|started playing music/i);
 const track=await say('Play loser by Tame Impala');assert.match(track.answer,/Spotify confirmed playback/i);
 const unclear=await say('Turn it down to clicks');assert.equal(unclear.tool_used,'Spotify verified control');assert.match(unclear.answer,/What volume percentage.*did not change/i);
 const pause=await say("No, it didn't but that's okay. Hey, uh, go ahead pause the song");assert.equal(pause.tool_used,'Spotify verified control');assert.match(pause.answer,/paused/i);assert.doesNotMatch(pause.answer,/Playing /i);
 const praise=await say('Awesome!');assert.notEqual(praise.tool_used,'Spotify verified control');assert.doesNotMatch(praise.answer,/Playing /i);
 const complaint=await say('No why did you play that what the heck');assert.doesNotMatch(complaint.answer,/Playing /i);
 const asrClose=await say('Clothes, Spotify. Clothes, Spotify.');assert.equal(asrClose.tool_used,'Allowlisted Windows companion');assert.match(asrClose.answer,/Spotify is closed|already closed/i);
 const repeated=await say('No clothes spotify');assert.equal(repeated.tool_used,'Allowlisted Windows companion');assert.match(repeated.answer,/already closed/i);assert.doesNotMatch(repeated.answer,/Playing /i);
 console.log(JSON.stringify({passed:true,voice_turns:9,checks:['prefaced open','bare play routed','verified requested track','unclear volume clarification','pause complaint cannot become search','praise cannot become title','complaint cannot become title','repeated ASR close','closed-state preservation']}));
})().catch(error=>{console.error(error.message);process.exit(1)});
