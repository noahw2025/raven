/* Spatial navigation is a projection of persisted work, not another scheduler. */
const RavenWorld={items:[],busy:false,last:0,selected:'active',stations:[
 {id:'research',name:'Research Lab',subtitle:'Explore · compare · understand',x:24,y:26,color:'#80e8ff',glyph:'⌕'},
 {id:'career',name:'Career Office',subtitle:'Discover your next chapter',x:70,y:21,color:'#ffc690',glyph:'▤'},
 {id:'graph',name:'Memory Core',subtitle:'Connected knowledge',x:12,y:62,color:'#b6a0ff',glyph:'◇'},
 {id:'studio',name:'Content Studio',subtitle:'Ideas into real artifacts',x:81,y:59,color:'#ff92c9',glyph:'◈'},
 {id:'hermes',name:'Hermes Workshop',subtitle:'Tools with a real connection',x:34,y:85,color:'#95f6c4',glyph:'⌘'},
 {id:'missions',name:'Operations',subtitle:'Every task. One place.',x:63,y:85,color:'#ffdf7a',glyph:'◎'}]};
function worldBuilding(station){
 return `<button class="world-station" data-station="${station.id}" style="--x:${station.x}%;--y:${station.y}%;--station:${station.color}" aria-label="Open ${station.name}"><svg viewBox="0 0 160 105" aria-hidden="true"><path class="island" d="M8 67 75 36 151 65 84 99Z"/><path class="wall-left" d="M39 43 82 62 82 83 39 64Z"/><path class="wall-right" d="M82 62 122 43 122 65 82 83Z"/><path class="roof" d="M39 43 80 23 122 43 82 62Z"/><path class="window" d="M48 53 72 63 72 70 48 60Z M91 63 111 54 111 61 91 70Z"/><path class="antenna" d="M80 24V8m-5 0h10"/><circle class="station-beacon" cx="80" cy="8" r="4"/><text x="80" y="49" text-anchor="middle">${station.glyph}</text><g class="data-sparks"><rect x="20" y="30" width="5" height="7"/><rect x="130" y="25" width="5" height="7"/><rect x="115" y="8" width="5" height="7"/></g></svg><strong>${station.name}</strong><small class="station-summary">${station.subtitle}</small><span class="station-detail"></span></button>`;
}
command=async function(){
 $('#view').innerHTML=`<section class="world-heading"><div><div class="eyebrow">YOUR PERSONAL INTELLIGENCE WORLD</div><h2>A little world.<br><em>Extraordinary possibilities.</em></h2></div><p>One RAVEN. Connected workspaces.<br>Explore a station or tell me what’s next.</p></section><section class="raven-world" aria-label="RAVEN interactive world"><div class="world-stars"></div><svg class="world-roads" viewBox="0 0 1000 600" preserveAspectRatio="none" aria-hidden="true"><path d="M500 300 240 156M500 300 700 126M500 300 120 372M500 300 810 354M500 300 340 510M500 300 630 510"/></svg><div class="world-core"><div class="core-ring"></div><span>RAVEN</span><small>PERSONAL OS / 01</small></div>${RavenWorld.stations.map(worldBuilding).join('')}<div id="worldAgent" class="world-agent" role="img" aria-label="RAVEN agent idle"><div class="agent-shadow"></div><div class="agent-body"><i></i><i></i></div><small id="agentState">Ready</small></div><div class="world-legend"><i></i><span id="worldSync">Connecting to live activity…</span><button id="worldMotion" class="ghost">Reduce motion</button></div></section><section class="world-console"><div><span class="eyebrow">TALK TO YOUR WORLD</span><h3>What are we making happen?</h3></div><form id="worldCommand"><input name="message" required aria-label="Message RAVEN" placeholder="Research a topic, find a role, create an image…"><button class="primary">Send ↗</button></form><button id="worldVoice" class="button">◉ Voice</button><button id="worldChat" class="ghost">Conversation</button><p id="worldReply" role="status"></p></section><section id="worldActivity" class="world-activity"></section>`;
 $$('[data-station]').forEach(b=>b.onclick=()=>route(b.dataset.station));
 $('#worldVoice').onclick=()=>startVoice();$('#worldChat').onclick=()=>route('talk');
 $('#worldMotion').onclick=()=>{document.documentElement.classList.toggle('world-still');$('#worldMotion').textContent=document.documentElement.classList.contains('world-still')?'Enable motion':'Reduce motion'};
 $('#worldCommand').onsubmit=async e=>{e.preventDefault();const f=e.target,b=$('button',f);b.disabled=true;try{const r=await api('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:new FormData(f).get('message'),conversation_id:state.conversation,channel:'text',ui_page:'command'}),deferUiAction:true});setActiveConversation(r.conversation_id);if($('#worldReply'))$('#worldReply').textContent=r.answer;f.reset();if(r.ui_action)await applyUiAction(r.ui_action);await refreshWorld()}catch(err){toast(err.message)}finally{b.disabled=false}};
 await refreshWorld();
};
async function refreshWorld(){
 if(RavenWorld.busy||!['command','missions'].includes(state.page))return;
 RavenWorld.busy=true;
 try{const data=await api('/world');RavenWorld.items=data.items;RavenWorld.last=Date.now();
  if(state.page==='command')drawWorld(data);if(state.page==='missions')drawOperations();
 }catch(err){if($('#worldSync'))$('#worldSync').textContent='Activity unavailable · '+err.message;$$('.world-station').forEach(el=>el.dataset.activity='unknown');if($('#agentState'))$('#agentState').textContent='Disconnected';if($('#worldAgent'))$('#worldAgent').dataset.state='unknown'}finally{RavenWorld.busy=false}
}
function drawWorld(data){
 if(!$('#worldSync'))return;
 $('#worldSync').textContent='Live records · '+new Date(data.observed_at).toLocaleTimeString();
 for(const station of RavenWorld.stations){const el=$(`[data-station="${station.id}"]`);if(!el)continue;
  const rows=data.items.filter(x=>x.workspace===station.id),active=rows.filter(x=>x.group==='active'),attention=rows.filter(x=>x.group==='waiting'),latest=rows[0];
  el.dataset.activity=active.length?'working':attention.length?'waiting':latest?.group||'idle';
  $('.station-summary',el).textContent=active.length?`${active.length} active · ${active[0].stage}`:attention.length?`${attention.length} need your attention`:latest?.group==='completed'?'Latest artifact ready':station.subtitle;
  $('.station-detail',el).textContent=(active[0]||latest)?.title||'Open workspace';el.title=rows.length?`${rows[0].title}\n${rows[0].detail}`:station.subtitle;
 }
 const task=data.items.find(x=>x.group==='active'),station=RavenWorld.stations.find(x=>x.id===task?.workspace),agent=$('#worldAgent');
 agent.style.left=(station?station.x+8:50)+'%';agent.style.top=(station?station.y-2:50)+'%';agent.dataset.state=task?'working':'idle';agent.setAttribute('aria-label',task?'RAVEN working on '+task.title:'RAVEN idle');$('#agentState').textContent=task?task.stage:'Ready';
 $('#worldActivity').innerHTML=`<div class="row"><h3>Signals from your world</h3><button id="allOperations" class="ghost">Open Operations ↗</button></div>${data.items.slice(0,3).map(x=>`<button class="world-signal" data-activity="${x.id}"><i class="${x.group}"></i><span><b>${escapeHtml(x.title)}</b><small>${escapeHtml(x.stage)} · ${escapeHtml(x.detail)}</small></span>${status(x.status)}</button>`).join('')||'<p>No activity yet. Your first real task will appear here.</p>'}`;
 $('#allOperations').onclick=()=>route('missions');$$('[data-activity]',$('#worldActivity')).forEach(b=>b.onclick=()=>route(data.items.find(x=>x.id===b.dataset.activity).workspace));
}
missions=async function(){
 $('#view').innerHTML=`<section class="world-heading"><div><div class="eyebrow">OPERATIONS / LIVE EXECUTION</div><h2>What is RAVEN<br><em>doing right now?</em></h2></div><p>One activity ledger across research, career,<br>content and supervised actions.</p></section><nav class="product-tabs" id="operationTabs">${['active','waiting','scheduled','completed','failed','archived'].map(t=>`<button data-group="${t}">${({waiting:'Waiting for me',archived:'Cancelled / archived'})[t]||t}</button>`).join('')}</nav><p class="subtle">Showing recent saved activity. Stage labels come from the worker; they are not estimated completion percentages.</p><div id="operationsList"></div>`;
 $('#operationTabs').onclick=e=>{const b=e.target.closest('[data-group]');if(b){RavenWorld.selected=b.dataset.group;drawOperations()}};await refreshWorld();
};
renderBackgroundTasks=async()=>{if(state.page==='missions')await refreshWorld()};
function drawOperations(){
 if(!$('#operationsList'))return;
 $$('[data-group]').forEach(b=>b.classList.toggle('active',b.dataset.group===RavenWorld.selected));
 const rows=RavenWorld.items.filter(x=>x.group===RavenWorld.selected);
 $('#operationsList').innerHTML=rows.map(x=>`<article class="operation-record"><div class="row"><div><small>${escapeHtml(x.workspace)} / ${escapeHtml(x.kind)}</small><h3>${escapeHtml(x.title)}</h3></div>${status(x.status)}</div><p>${escapeHtml(x.detail||x.stage)}</p>${x.error?`<p class="operation-error">${escapeHtml(x.error)}</p>`:''}<div class="row"><small>${fmtDate(x.updated_at)}</small><span><button class="button" data-open-work="${x.workspace}">Open workspace ↗</button>${x.artifact?`<a class="button" href="${escapeHtml(x.artifact)}">Open artifact</a>`:''}${x.kind==='research'&&x.group==='active'?`<button class="ghost" data-cancel-research="${x.id}">Cancel research</button>`:''}</span></div></article>`).join('')||`<div class="product-empty"><span>◎</span><h3>No ${escapeHtml(RavenWorld.selected)} work</h3><p>Only real saved activity appears here.</p></div>`;
 $$('[data-open-work]').forEach(b=>b.onclick=()=>route(b.dataset.openWork));$$('[data-cancel-research]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{await api('/research/projects/'+b.dataset.cancelResearch+'/cancel',{method:'POST'});await refreshWorld()}catch(e){toast(e.message)}finally{b.disabled=false}});
}
setInterval(()=>{if(!document.hidden)refreshWorld()},3500);
