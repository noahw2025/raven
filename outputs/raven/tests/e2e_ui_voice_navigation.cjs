const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
let cookie='';
async function post(route,body){const response=await fetch('http://127.0.0.1:8080/api'+route,{method:'POST',headers:{Cookie:cookie,Origin:'http://localhost:8080','Content-Type':'application/json'},body:JSON.stringify(body)});if(response.headers.get('set-cookie'))cookie=response.headers.get('set-cookie').split(';')[0];assert(response.ok,`${route}: HTTP ${response.status}`);return response.json()}
(async()=>{
 await post('/login',{password:env.RAVEN_ADMIN_PASSWORD});
 const content=await post('/chat',{message:"Hey Raven, let's move to the content page",channel:'voice',ui_page:'talk'});
 assert.deepEqual(content.ui_action,{type:'navigate',page:'studio',label:'Social Studio'});
 const memory=await post('/chat',{message:"Let's look into our memories",channel:'voice',ui_page:'studio'});
 assert.deepEqual(memory.ui_action,{type:'navigate',page:'memory',label:'Memory Vault'});
 const graph=await post('/chat',{message:'Could you switch to the knowledge page?',channel:'voice',ui_page:'memory'});
  assert.deepEqual(graph.ui_action,{type:'navigate',page:'graph',label:'Knowledge Graph'});
 const spokenGraph=await post('/chat',{message:"Okay, I really appreciate that actually let's go into the knowledge and graph, okay?",channel:'voice',ui_page:'studio'});
 assert.deepEqual(spokenGraph.ui_action,{type:'navigate',page:'graph',label:'Knowledge Graph'});
 const shortGraph=await post('/chat',{message:'Go to knowledge.',channel:'voice',ui_page:'research'});
 assert.deepEqual(shortGraph.ui_action,{type:'navigate',page:'graph',label:'Knowledge Graph'});
 const politeGraph=await post('/chat',{message:'Okay, amazing. Now can you go to knowledge?',channel:'voice',ui_page:'career'});
 assert.deepEqual(politeGraph.ui_action,{type:'navigate',page:'graph',label:'Knowledge Graph'});assert.equal(politeGraph.tokens.total,0);
 const zoom=await post('/chat',{message:'Zoom in here',channel:'voice',ui_page:'graph'});
 assert.deepEqual(zoom.ui_action,{type:'graph_zoom',direction:'in',label:'Knowledge Graph'});
 const spotifyNodes=await post('/chat',{message:'Zoom in on the open Spotify node please',channel:'voice',ui_page:'graph'});
 assert.equal(spotifyNodes.ui_action.type,'graph_filter');assert.equal(spotifyNodes.ui_action.query,'spotify');assert(Array.isArray(spotifyNodes.ui_action.node_ids));assert.equal(spotifyNodes.tokens.total,0);assert.equal(spotifyNodes.tool_used,'RAVEN interface control');
 const memoryOnly=await post('/chat',{message:'Can you select memories for me, please',channel:'voice',ui_page:'graph'});
 assert.equal(memoryOnly.ui_action.type,'graph_filter');assert.equal(memoryOnly.ui_action.object_type,'memory');
 const clarify=await post('/chat',{message:'Zoom out here',channel:'voice',ui_page:'studio'});
 assert.equal(clarify.ui_action.type,'clarify');assert.match(clarify.answer,/Knowledge Graph/i);
 console.log(JSON.stringify({passed:true,voice_requests:10,spotify_semantic_matches:spotifyNodes.ui_action.node_ids.length,checks:['content navigation','memory navigation','knowledge navigation','natural long-form knowledge navigation','polite knowledge navigation','short knowledge navigation','graph zoom','semantic Spotify focus','memory-only filter','ambiguous zoom clarification']}));
})().catch(error=>{console.error(error.message);process.exit(1)});
