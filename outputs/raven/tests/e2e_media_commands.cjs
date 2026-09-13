const fs=require('fs');const path=require('path');const assert=require('assert');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
const origin='http://127.0.0.1:8080';let cookie='',conversation_id=null;
async function request(route,options={}){const response=await fetch(origin+route,{...options,headers:{...(options.headers||{}),...(cookie?{Cookie:cookie}:{})}});const setCookie=response.headers.get('set-cookie');if(setCookie)cookie=setCookie.split(';')[0];const body=await response.text();if(!response.ok)throw new Error(`${route} ${response.status}: ${body}`);return JSON.parse(body)}
async function say(message){const result=await request('/api/chat',{method:'POST',headers:{Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify({message,conversation_id,channel:'text',ui_page:'tools'})});conversation_id=result.conversation_id;return result}
(async()=>{
  await request('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});
  let r=await say('OpenSpotify!');assert.equal(r.tool_used,'Spotify verified control');assert(/Spotify/i.test(r.answer),r.answer);
  r=await say('Yeah, play Good Morning by Kanye West');assert.equal(r.tool_used,'Spotify verified control');assert(/Spotify/i.test(r.answer));assert(/authorization|confirmed playback|Playing /i.test(r.answer));
  r=await say('No, it is not playing');assert.equal(r.tool_used,'Spotify verified control');assert(/did not start|not confirmed/i.test(r.answer));assert(!/is now playing/i.test(r.answer));
  r=await say('pause Spotify');assert.equal(r.tool_used,'Spotify verified control');assert(/not authorized|confirmed|no active playback device/i.test(r.answer),r.answer);
  r=await say('skip to the next song');assert.equal(r.tool_used,'Spotify verified control');assert(/dispatched|confirmed|no active playback device/i.test(r.answer),r.answer);
  r=await say('set Spotify volume to 40 percent');assert.equal(r.tool_used,'Spotify verified control');assert(/not authorized|confirmed|no active playback device/i.test(r.answer),r.answer);
  r=await say('what is playing on Spotify?');assert.equal(r.tool_used,'Spotify verified control');assert(/not authorized|reports|no active playback device/i.test(r.answer),r.answer);
  r=await say('open ChatGPT');assert.equal(r.tool_used,'Allowlisted Windows companion');assert(/ChatGPT/i.test(r.answer));
  r=await say('open Discord');assert.equal(r.tool_used,'Allowlisted Windows companion');assert(/Discord/i.test(r.answer));
  r=await say('launch Apex Legends');assert.equal(r.tool_used,'Allowlisted Windows companion');assert(/Apex Legends is open/i.test(r.answer),r.answer);
  r=await say('join Discord channel unconfigured-demo');assert.equal(r.tool_used,'Discord allowlisted channel resolver');assert(/do not have a server-side Discord channel alias/i.test(r.answer));
  r=await say('find videos about local AI voice agents on YouTube');assert.equal(r.tool_used,'YouTube public video search');assert(!/invent/i.test(r.answer)||/did not invent/i.test(r.answer));
  r=await say('Hey Raven, can you open YouTube for me with videos of cats?');assert.equal(r.tool_used,'YouTube verified browser control');assert(/opened YouTube in Chrome with results for cats/i.test(r.answer),r.answer);assert.equal(r.ui_action,null);
  r=await say('Open Spotify, then play Good Morning by Kanye West, and open YouTube with videos of cats');assert.equal(r.tool_used,'RAVEN verified multi-step executor');assert(/Spotify/i.test(r.answer));assert(/YouTube/i.test(r.answer));
  process.stdout.write(JSON.stringify({passed:true,spotify:true,spotify_truthful:true,spotify_transport_controls:true,chatgpt:true,discord:true,apex:true,discord_alias_guard:true,youtube_search:true,youtube_chrome_dispatch:true,multi_step:true}));
})().catch(error=>{console.error(error.stack);process.exit(1)});
