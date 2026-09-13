const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
let cookie='',conversation_id=null;
async function say(message,ui_page='talk'){const response=await fetch('http://127.0.0.1:8080/api/chat',{method:'POST',headers:{Cookie:cookie,Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify({message,conversation_id,channel:'voice',ui_page})});assert(response.ok,`${message}: HTTP ${response.status}`);const result=await response.json();conversation_id=result.conversation_id;return result}
(async()=>{
 const login=await fetch('http://127.0.0.1:8080/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});assert(login.ok);cookie=login.headers.get('set-cookie').split(';')[0];
 const research=await say('Hey, take me to the research center.');assert.equal(research.ui_action.page,'research');assert.equal(research.tool_used,'RAVEN interface control');
 const opened=await say("Alright, let's get some music playing open Spotify");assert.equal(opened.tool_used,'Spotify verified control');assert.match(opened.answer,/Spotify is open/i);
 const played=await say('Okay, play Good Morning by Kanye West');assert.match(played.answer,/Spotify confirmed playback/i);
 const paused=await say('Pause the song');assert.match(paused.answer,/(?:confirmed.*paused|already paused)/i);
 const closed=await say("Thank you, Raven. I really appreciate that. Here's what I'm gonna have you do. Can you close Spotify?");assert.equal(closed.tool_used,'Allowlisted Windows companion');assert.match(closed.answer,/Spotify is closed/i);
 const blockedSkip=await say('Skip Song on Spotify');assert.match(blockedSkip.answer,/Spotify is closed.*did not send/i);assert.doesNotMatch(blockedSkip.answer,/confirmed.*skipped/i);
 await say('Open Spotify');await say('Play Good Morning by Kanye West');
 const next=await say('Skip the song');assert.match(next.answer,/confirmed.*next track/i);
 const previous=await say('Backtrack one song skip backwards');assert.match(previous.answer,/confirmed.*previous track/i);
 const oddPause=await say('So pause on.');assert.match(oddPause.answer,/(?:confirmed.*paused|already paused)/i);
 const correction=await say("No, it didn't pause the song");assert.match(correction.answer,/reports it is paused/i);
 const finalClose=await say('Blows Spotify');assert.match(finalClose.answer,/Spotify is closed/i);
 console.log(JSON.stringify({passed:true,voice_turns:13,checks:['research center alias','prefaced open','verified play/pause','prefaced close','closed-state skip block','next/previous state verification','ASR pause variants','correction handling','ASR close variant']}));
})().catch(error=>{console.error(error.message);process.exit(1)});
