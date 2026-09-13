// One primary destination per activity; existing deep links remain valid.
const WORKSPACES=[
 ['command','Assistant','01',[['command','Overview'],['talk','Conversation']]],
 ['forge','Forge','02',[['forge','Engineering workspace']]],
 ['world','World','◉',[['world','World intelligence']]],
 ['research','Research','03',[['research','Research Lab'],['search-setup','Search setup']]],
 ['career','Career','04',[['career','Job workspace']]],
 ['studio','Content','05',[['studio','Content Studio']]],
 ['missions','Operations','06',[['missions','Activity'],['goals','Goals & tasks'],['trust','Approvals']]],
 ['graph','Knowledge','07',[['graph','Vector map'],['memory','Memory library'],['memory-engine','How memory works']]],
 ['tools','Capabilities','08',[['tools','Connections'],['hermes','Hermes Tools'],['roadmap','Build roadmap'],['departments','Departments']]],
 ['system','System','09',[['system','Activity'],['models','Models & costs'],['settings','Privacy & settings']]]
];
NAV.splice(0,NAV.length,...WORKSPACES.map(([id,name,icon])=>[id,name,icon]));
$('#closeInspector').onclick=()=>{$('#inspector').dataset.open='false'};
new MutationObserver(()=>{if(!$('#inspectorBody .empty-lens'))$('#inspector').dataset.open='true'}).observe($('#inspectorBody'),{childList:true});
const originalDashboard=command;
const originalCareer=career;
career=async function(){
 await originalCareer();
 const source=$('#careerSourceForm')?.closest('article');
 if(source){const advanced=document.createElement('details');advanced.className='panel';advanced.innerHTML='<summary>Optional: follow a specific employer’s job feed</summary><p>Use this only when you already know the employer. Regular job search below does not require a feed.</p>';source.before(advanced);advanced.append(source)}
 $('#view').insertAdjacentHTML('afterbegin','<section class="panel"><div class="eyebrow">YOUR NEXT ROLE</div><h2>Find a role. Build your application. Review before sending.</h2><p>Save your factual career history in My Profile, search for specific jobs, then build a tailored resume and cover letter from a job card. Applications keeps the exact versions and submission evidence.</p></section>');
};
const originalStudio=studio;
studio=async function(){
 await originalStudio();
 $('#view').insertAdjacentHTML('afterbegin',`<section class="panel"><div class="eyebrow">CREATE / PREVIEW / KEEP</div><h2>Start with one idea.</h2><p>Generate an image or video directly. No campaign, social account, or text-model key is needed. Nothing is published.</p><form id="quickMedia" class="stack"><label>Describe your visual<textarea name="prompt" required minlength="3" maxlength="4000" placeholder="A luminous futuristic city at dusk, mint neon and violet skies"></textarea></label><div class="row"><select name="kind" aria-label="Media type"><option value="image">Image</option><option value="video">Video · slower, GPU intensive</option></select><button class="primary">Generate preview</button></div><p id="quickMediaStatus" role="status"></p></form></section>`);
 $('#quickMedia').onsubmit=async e=>{e.preventDefault();const f=new FormData(e.target),b=$('button',e.target),label=$('#quickMediaStatus');b.disabled=true;label.textContent='Sending your prompt to the local media engine…';try{const r=await api('/social/quick-media',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({prompt:f.get('prompt'),kind:f.get('kind')})});label.textContent='Queued. Your draft is saved; open it below to follow generation.';toast('Media queued · saved in Content');await studio()}catch(error){label.textContent=error.message}finally{b.disabled=false}};
};
command=async function(){
 await originalDashboard();
 $('.command-hero')?.remove();
 $('#view').insertAdjacentHTML('afterbegin',`<section class="assistant-stage"><div class="reactor" aria-hidden="true"><b>R</b></div><div id="reactorState" role="status">READY FOR VOICE OR TEXT</div><h2>Your ideas. In motion.</h2><p>Talk to RAVEN, explore what you know, or give a background agent something to work on.</p><div class="row"><button class="primary" id="heroVoice">Talk to RAVEN</button><button class="button" id="heroText">Write a message</button></div><div class="assistant-shortcuts"><button data-destination="research">Explore a topic ↗</button><button data-destination="career">Find my next role ↗</button><button data-destination="studio">Create something ↗</button><button data-destination="graph">Explore my memory ↗</button></div></section>`);
 $('#heroVoice').onclick=()=>startVoice();$('#heroText').onclick=()=>route('talk');
 $$('[data-destination]').forEach(b=>b.onclick=()=>route(b.dataset.destination));
 setRavenState(document.documentElement.dataset.ravenState||'ready');
};
let workspaceNavigation=0;
route=async function(page){
 if(state.page==='world'&&page!=='world')window.RavenGeo?.dispose();
 const epoch=++workspaceNavigation;state.page=page;
 const workspace=WORKSPACES.find(w=>w[3].some(t=>t[0]===page))||WORKSPACES[0];
 $$('.navbtn').forEach(b=>b.classList.toggle('active',b.dataset.page===workspace[0]));
 $('#breadcrumb').textContent=workspace[1].toUpperCase();$('#pageTitle').textContent=workspace[1];
 try{
  if(page==='hermes'){
   const d=await api('/hermes/tools');
   $('#view').innerHTML=`<section class="panel"><div class="eyebrow">HERMES / TOOL RUNTIME</div><h2>Tools, MCP connections, and runtime health.</h2><p>${escapeHtml(d.detail)}</p><div class="row">${status(d.connected?'connected':'unavailable')}${status(d.reasoner_ready?'configured':'needs setup')}</div><p>Model: ${escapeHtml(d.model)} · OpenRouter key: ${d.openrouter_configured?'configured server-side':'not configured'}</p><p>Research Lab is the single place to start and inspect research. It can use Hermes for web discovery while keeping one project, progress view, evidence ledger, report, and fallback chain.</p><button class="primary" id="openResearchLab">OPEN RESEARCH LAB →</button></section>`;
   $('#openResearchLab').onclick=()=>route('research');
  }else if(['models','memory-engine','search-setup'].includes(page)){
   await tools();const key={models:'models','memory-engine':'memory','search-setup':'search'}[page];$(`[data-ops="${key}"]`)?.click();$('.ops-hero')?.remove();$('.ops-tabs')?.remove();
  }else{
   await ({command,talk,forge:window.forgeWorkspace,world:window.worldWorkspace,memory,graph:knowledgeGraph,research,goals,missions,studio,career,departments,tools,roadmap,trust,system,settings}[page]||command)();
   if(page==='tools')$('.ops-tabs')?.remove();
  }
  if(epoch!==workspaceNavigation)return;
  $('#workspaceTabs')?.remove();
  if(workspace[3].length>1){
   const tabs=document.createElement('nav');tabs.id='workspaceTabs';tabs.setAttribute('aria-label',workspace[1]+' views');
   tabs.innerHTML=workspace[3].map(([id,label])=>`<button class="${id===page?'active':''}" aria-current="${id===page?'page':'false'}" data-view="${id}">${label}</button>`).join('');
   $('#view').before(tabs);tabs.onclick=e=>{const b=e.target.closest('[data-view]');if(b)route(b.dataset.view)};
  }
 }catch(error){toast(error.message)}
};

// Dialogs are usable even when the context sidebar is hidden on small screens.
openKnowledgeNode=async function(node){
 document.querySelector('#nodeEditor')?.remove();
 const dialog=document.createElement('dialog');dialog.id='nodeEditor';dialog.setAttribute('aria-label','Knowledge object editor');
 document.body.append(dialog);
 dialog.innerHTML='<p>Loading saved object…</p>';dialog.showModal();
 try{
  if(node.type!=='memory'){
   const destination={document:'memory',goal:'goals',task:'goals',model:'tools'}[node.type]||'memory';
   dialog.innerHTML=`<div class="row"><h2>${escapeHtml(node.label)}</h2><button data-close aria-label="Close editor">×</button></div><p>This is a ${escapeHtml(node.type)} object, not an editable memory.</p><p>${escapeHtml(node.layout_basis||'Canonical relationship')}</p><button class="primary" data-open>OPEN ITS WORKSPACE</button>`;
   $('[data-open]',dialog).onclick=()=>{dialog.close();route(destination)};
  }else{
   const item=(await api('/memories')).find(m=>String(m.id)===String(node.id));
   if(!item)throw new Error('This memory no longer exists. Refresh the map.');
   dialog.innerHTML=`<form class="stack"><div class="row"><div><div class="eyebrow">SAVED MEMORY</div><h2>Edit what RAVEN remembers</h2></div><button type="button" data-close aria-label="Close editor">×</button></div><label>Memory<textarea name="content" required maxlength="8000">${escapeHtml(item.content)}</textarea></label><div class="two"><label>Category<input name="kind" value="${escapeHtml(item.kind)}" required></label><label>Importance<input name="importance" type="number" min="1" max="5" value="${item.importance}"></label></div><label class="check"><input name="excluded" type="checkbox" ${item.excluded?'checked':''}> Exclude from AI retrieval</label><p class="subtle">Saving recalculates this memory’s embedding. Map distances are a 3D approximation, not confidence scores.</p><p role="status" id="nodeSaveStatus"></p><div class="row"><button class="primary" type="submit">SAVE MEMORY</button><button type="button" class="danger-button" data-delete>DELETE MEMORY</button></div><div data-confirm hidden><p>Permanently delete this memory and its retrieval links? This cannot be undone.</p><button type="button" class="danger-button" data-confirm-delete>YES, DELETE PERMANENTLY</button><button type="button" data-keep>KEEP MEMORY</button></div></form>`;
   const refresh=async()=>{
    if(state.page==='graph'){
     const query=$('#graphSearch').value,mode=state.graphMode,type=$('#graphType').value;
     await knowledgeGraph();state.graphMode=mode;$('#graphSearch').value=query;$('#graphType').value=type;
     $$('[data-graph-mode]').forEach(b=>b.classList.toggle('active',b.dataset.graphMode===mode));renderConstellation(state.graph);
    }
    await refreshDashboard();
   };
   $('form',dialog).onsubmit=async e=>{
    e.preventDefault();const form=new FormData(e.target);const button=$('[type=submit]',dialog);button.disabled=true;
    try{await api('/memories/'+item.id,{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({content:form.get('content'),kind:form.get('kind'),importance:Number(form.get('importance')),excluded:form.has('excluded'),sensitive:item.sensitive,pinned:item.pinned,rationale:'Owner correction from vector map'})});await refresh();dialog.close();toast('Memory saved · vector refreshed')}
    catch(error){$('#nodeSaveStatus').textContent=error.message}finally{button.disabled=false}
   };
   $('[data-delete]',dialog).onclick=()=>{$('[data-confirm]',dialog).hidden=false};
   $('[data-keep]',dialog).onclick=()=>{$('[data-confirm]',dialog).hidden=true};
   $('[data-confirm-delete]',dialog).onclick=async()=>{
    const button=$('[data-confirm-delete]',dialog);button.disabled=true;
    try{await api('/memories/'+item.id,{method:'DELETE'});await refresh();dialog.close();toast('Memory permanently deleted')}
    catch(error){$('#nodeSaveStatus').textContent=error.message}finally{button.disabled=false}
   };
  }
  $('[data-close]',dialog).onclick=()=>dialog.close();
 }catch(error){dialog.innerHTML=`<p>${escapeHtml(error.message)}</p><button data-close>Close</button>`;$('[data-close]',dialog).onclick=()=>dialog.close()}
 dialog.addEventListener('close',()=>dialog.remove(),{once:true});
};

renderConstellation=function(data){
 const svg=$('#graphCanvas'),list=$('#graphList');if(!svg)return;
 const mode=state.graphMode||'3d',camera={yaw:0,pitch:0,zoom:1};let drag=null,moved=false,focusIds=null;
 window.ravenGraphZoom=direction=>{if(direction==='reset'){camera.yaw=0;camera.pitch=0;camera.zoom=1}else camera.zoom=Math.max(.3,Math.min(3,camera.zoom*(direction==='out'?.82:1.22)));draw()};
 window.ravenGraphControl=direction=>{if(direction==='left')camera.yaw-=.28;if(direction==='right')camera.yaw+=.28;if(direction==='up')camera.pitch=Math.max(-1.2,camera.pitch-.2);if(direction==='down')camera.pitch=Math.min(1.2,camera.pitch+.2);draw()};
 list.hidden=mode!=='list';svg.hidden=mode==='list';
 const unprojected=data.nodes.filter(n=>!n.position),positions={};
 data.nodes.forEach(n=>{if(n.position)positions[n.id]=n.position;else{const i=unprojected.indexOf(n);positions[n.id]=[-1.25,(i-(unprojected.length-1)/2)*.12,0]}});
 const note=$('.graph-foot');if(note)note.innerHTML=`<span>DRAG: ROTATE · SCROLL: ZOOM · CLICK: EDIT</span><span>PCA · ${Math.round((data.meta.variance_retained||0)*100)}% VARIANCE RETAINED</span><span>UNPROJECTED OBJECTS: LEFT RAIL</span>`;
 const draw=()=>{
  const query=$('#graphSearch').value.toLowerCase(),type=$('#graphType').value;
  const nodes=data.nodes.filter(n=>(!focusIds||focusIds.has(String(n.id)))&&(!type||n.type===type)&&(!query||focusIds||n.label.toLowerCase().includes(query)));
  if(mode==='list'){
   list.innerHTML=nodes.map(n=>`<button class="graph-list-row" data-node="${n.id}"><b>${escapeHtml(n.label)}</b><span>${n.type} · ${n.semantic_cluster?`semantic cluster ${n.semantic_cluster} · `:''}${n.position?'vector projected':'unprojected'}</span></button>`).join('');
   $$('[data-node]',list).forEach(b=>b.onclick=()=>openKnowledgeNode(nodes.find(n=>n.id===b.dataset.node)));return;
  }
  const w=svg.clientWidth||1000,h=svg.clientHeight||650,scale=Math.min(w*.29,h*.36)*camera.zoom,points={};
  for(const n of nodes){const [x,y,z0]=positions[n.id],z=mode==='2d'?0:z0,cy=Math.cos(camera.yaw),sy=Math.sin(camera.yaw),cp=Math.cos(camera.pitch),sp=Math.sin(camera.pitch),rx=x*cy-z*sy,rz=x*sy+z*cy,ry=y*cp-rz*sp,depth=y*sp+rz*cp,p=mode==='2d'?1:3.5/(3.5+depth);points[n.id]={x:w*.52+rx*scale*p,y:h*.53+ry*scale*p,z:depth}}
  const labels=[];svg.setAttribute('viewBox',`0 0 ${w} ${h}`);
  svg.innerHTML=data.edges.filter(e=>e.type!=='embedded_by'&&points[e.source]&&points[e.target]).map(e=>{const a=points[e.source],b=points[e.target];return `<line class="vector-edge" x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"><title>${escapeHtml(e.type)} · ${Math.round((e.confidence||0)*100)}%</title></line>`}).join('')+nodes.map(n=>{
   const p=points[n.id],color={memory:'#49e4ff',document:'#ffae55',goal:'#a99bff',task:'#ffce77',model:'#8f9bb9'}[n.type],text=n.label.slice(0,36),width=Math.min(224,text.length*6+16);let box=null;
   for(const dy of [-25,12,-49,36,-73,60]){const candidate={x:Math.min(w-width-5,Math.max(5,p.x+12)),y:p.y+dy,w:width,h:22};if(candidate.y>4&&candidate.y+22<h&&!labels.some(b=>candidate.x<b.x+b.w&&candidate.x+width>b.x&&candidate.y<b.y+b.h&&candidate.y+22>b.y)){box=candidate;labels.push(box);break}}
   return `<g class="vector-node" role="button" tabindex="0" aria-label="${escapeHtml(n.type+': '+n.label)}" data-node="${n.id}"><title>${escapeHtml(n.label)} — ${escapeHtml(n.layout_basis||n.type)}${n.semantic_cluster?` — semantic cluster ${n.semantic_cluster} (${n.cluster_size})`:''}</title><circle cx="${p.x}" cy="${p.y}" r="12" fill="transparent"/><circle cx="${p.x}" cy="${p.y}" r="4.5" fill="${color}" stroke="${color}"/>${box?`<line x1="${p.x}" y1="${p.y}" x2="${box.x}" y2="${box.y+11}" stroke="${color}" opacity=".3"/><rect x="${box.x}" y="${box.y}" width="${width}" height="22" rx="4"/><text x="${box.x+7}" y="${box.y+15}">${escapeHtml(text)}</text>`:''}</g>`;
  }).join('');
  $$('[data-node]',svg).forEach(el=>{const open=()=>openKnowledgeNode(data.nodes.find(n=>n.id===el.dataset.node));el.onclick=()=>{if(!moved)open()};el.onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();open()}}});
 };
 svg.onpointerdown=e=>{moved=false;drag={x:e.clientX,y:e.clientY,yaw:camera.yaw,pitch:camera.pitch};if(!e.target.closest('[data-node]'))svg.setPointerCapture(e.pointerId)};
 svg.onpointermove=e=>{if(!drag||Math.hypot(e.clientX-drag.x,e.clientY-drag.y)<5)return;moved=true;camera.yaw=drag.yaw+(e.clientX-drag.x)*.006;camera.pitch=drag.pitch+(e.clientY-drag.y)*.006;draw()};
 svg.onpointerup=svg.onpointercancel=()=>{drag=null};svg.onwheel=e=>{e.preventDefault();camera.zoom=Math.max(.3,Math.min(3,camera.zoom*(e.deltaY>0?.9:1.1)));draw()};
 $('#graphSearch').oninput=()=>{focusIds=null;draw()};$('#graphType').onchange=draw;
 window.ravenGraphFilter=action=>{
  const ids=(action.node_ids||[]).map(String);focusIds=Array.isArray(action.node_ids)?new Set(ids):null;
  $('#graphSearch').value=action.query||'';$('#graphType').value=action.object_type||'';
  if(action.zoom&&focusIds)camera.zoom=Math.min(2.4,Math.max(1.35,camera.zoom*1.35));
  $('#graphDepth').textContent=focusIds?`SEMANTIC / ${ids.length}`:((action.object_type||action.query)?'FILTERED':'GLOBAL');
  draw();toast(focusIds?`${ids.length} semantically relevant memories highlighted`:'Knowledge field updated');
 };
 // The older page binds filterGraph after rendering; keep its hook functional.
 filterGraph=draw;draw();
};
