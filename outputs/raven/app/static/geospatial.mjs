import {installRenderGovernor,governorRequestRender,holdContinuousRender,releaseContinuousRender,_resetRenderGovernorForTest,getRenderGovernorDiagnostics} from './geo/renderGovernor.mjs';

const COLORS={aircraft:'#64e5ff',military:'#f5b971',satellites:'#a7a0ff',ships:'#6ef2cd',earthquakes:'#ff8976',environment:'#c3e88d',cameras:'#f4db96',launches:'#f5a9e4'};
const HOME={latitude:33.749,longitude:-84.388,altitude:16000000,region:'Earth'};
const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const label=s=>String(s).replaceAll('_',' ');
const stamp=s=>s?new Date(s).toLocaleString():'Not reported';

/** WorldLayer owns its datasource, records, polling, and disposal. */
class WorldLayer {
 constructor(world,provider){this.world=world;this.provider=provider;this.id=provider.id;this.enabled=false;this.loading=false;this.records=new Map();this.next=0;this.state='idle';this.source=new world.C.CustomDataSource(this.id);this.source.clustering.enabled=true;this.source.clustering.pixelRange=35;this.source.clustering.minimumClusterSize=4;this.source.clustering.clusterEvent.addEventListener((entities,cluster)=>{cluster.label.font='12px sans-serif';cluster.label.fillColor=world.C.Color.WHITE;cluster.label.showBackground=true;cluster.label.backgroundColor=world.C.Color.fromCssColorString('#173148').withAlpha(.85);cluster.label.pixelOffset=new world.C.Cartesian2(0,-8);cluster.point.show=true;cluster.point.pixelSize=10;cluster.point.color=world.C.Color.fromCssColorString(COLORS[this.id]);});world.viewer.dataSources.add(this.source)}
 async toggle(enabled){this.enabled=enabled;this.source.show=enabled;this.world.renderLayers();if(enabled)await this.refresh(true);else if(this.world.selected?.layer===this.id)this.world.select(null);governorRequestRender('layer-toggle')}
 async refresh(force=false){
  const w=this.world;if(!this.enabled||this.loading||w.dead||document.hidden||(!force&&Date.now()<this.next))return;
  this.loading=true;this.state='connecting';w.renderLayers();
  try{
   const v=w.viewport(),data=await w.api(`/geo/feed/${this.id}?latitude=${v.latitude}&longitude=${v.longitude}`,{signal:w.abort.signal});if(w.dead||!this.enabled)return;
   this.state=data.status;this.freshness=data.freshness;this.detail=data.detail;this.at=data.fetched_at;this.next=Date.now()+Math.max(30,this.provider.ttl)*1000;
   this.source.entities.suspendEvents();this.source.entities.removeAll();this.records.clear();
   for(const row of data.entities){
    if(this.id==='satellites'){try{row.satrec=window.satellite.twoline2satrec(...row.tle)}catch{continue}}
    const pos=w.position(row);if(!pos)continue;
    const entity=this.source.entities.add({id:row.id,name:row.name,position:pos,point:{pixelSize:this.id==='earthquakes'?Math.max(6,Math.min(17,Number(row.metadata.magnitude||1)*2)):6,color:w.C.Color.fromCssColorString(COLORS[this.id]),outlineColor:w.C.Color.fromCssColorString('#101b2c'),outlineWidth:1},label:{text:row.name,font:'12px sans-serif',show:false,pixelOffset:new w.C.Cartesian2(0,-18),fillColor:w.C.Color.WHITE,showBackground:true,backgroundColor:w.C.Color.fromCssColorString('#091321')}});
    row.entity=entity;this.records.set(row.id,row);
   }
   this.source.entities.resumeEvents();
   if(w.selected?.layer===this.id){const updated=this.records.get(w.selected.id);w.select(updated||null)}
   governorRequestRender('provider-refresh');
  }catch(e){if(!w.dead&&e.name!=='AbortError'){this.state=this.records.size?'stale':'unavailable';this.detail='The source did not respond. Retry shortly.';this.next=Date.now()+60000}}
  finally{this.loading=false;if(!w.dead)w.renderLayers()}
 }
 dispose(){this.enabled=false;this.records.clear();if(!this.world.viewer.isDestroyed())this.world.viewer.dataSources.remove(this.source,true)}
}

export async function mount(root,services){
 const started=performance.now(),C=window.Cesium;C.Ion.defaultAccessToken='';
 root.innerHTML=`<section class="geo-workspace" aria-label="World intelligence">
  <header class="geo-header"><div><div class="eyebrow">RAVEN / WORLD INTELLIGENCE</div><h2>A wider perspective.</h2><p>Public signals. Source-backed context. One connected assistant.</p></div><button id="geoPalette">Commands <kbd>Ctrl K</kbd></button></header>
  <div class="geo-toolbar"><form id="geoSearch"><label class="sr-only" for="geoLocation">Find a location</label><input id="geoLocation" maxlength="160" placeholder="Find a city, airport, or place" required><button type="submit">Find location</button></form><label class="geo-basemap">Map style<select id="geoBasemap"><option value="earth">Earth · offline</option><option value="imagery">Satellite imagery · Esri</option></select></label><button id="geoHome">Home view</button><button id="geoZoomOut" aria-label="Zoom out">−</button><button id="geoZoomIn" aria-label="Zoom in">+</button></div>
  <div id="geoPlaces" hidden></div>
  <div class="geo-layout">
   <aside class="geo-layers"><div class="eyebrow">DATA LAYERS</div><h3>Choose your signals</h3><p>Only enabled layers are fetched. No simulated tracks.</p><div id="geoLayers"></div><details><summary>Coverage & credits</summary><div id="geoCredits"></div><p>Camera and location searches are public services. Your microphone, model keys, and private memories are not sent to data providers.</p><p>God’s Eye View · Bilawal Sidhu (MIT). CesiumJS & satellite.js.</p></details></aside>
   <div class="geo-stage"><div id="geoGlobe" aria-label="Interactive 3D Earth"></div><div class="geo-hud"><span id="geoRegion">Earth</span><small id="geoCoords"></small></div><div class="geo-legend">Drag to orbit · Scroll to zoom · Click an object to inspect</div><div id="geoEngineError" hidden role="alert"></div></div>
   <aside class="geo-inspector" aria-label="Selected world object"><div class="eyebrow">CONTEXT / INTELLIGENCE</div><div id="geoSelection"><div class="geo-empty">◎</div><h3>Look closer.</h3><p>Select an object on Earth to see its source, reported details, and what RAVEN can learn from it.</p></div><div class="geo-inspector-actions"><button id="geoAsk">Ask about this view</button><button id="geoResearch">Research this area</button><button id="geoRemember">Save this location</button><button id="geoStopFollow" hidden>Stop following</button></div><details class="geo-visible"><summary>Objects in this view <span id="geoCount">0</span></summary><div id="geoVisible"></div></details></aside>
  </div>
  <footer class="geo-assistant"><div class="geo-assistant-head"><b><i></i> RAVEN · WORLD</b><span id="geoStatus" role="status">Connecting the globe…</span><button id="geoVoice">Use voice</button></div><div id="geoAnswer" class="geo-answer" aria-live="polite"><p>Try “Take me to Atlanta and show aircraft.” Select a marker, then ask “What am I looking at?”</p></div><form id="geoPrompt"><label class="sr-only" for="geoMessage">Ask RAVEN about World</label><input id="geoMessage" maxlength="2000" placeholder="Navigate, explore a signal, or ask about this area…" required><button type="submit">Ask RAVEN</button></form><a id="geoResearchLink" href="#" hidden>Open the queued research project →</a></footer>
 </section>`;
 const $=s=>root.querySelector(s);
 let viewer;
 try{viewer=new C.Viewer('geoGlobe',{baseLayer:false,baseLayerPicker:false,geocoder:false,homeButton:false,sceneModePicker:false,navigationHelpButton:false,animation:false,timeline:false,fullscreenButton:false,selectionIndicator:false,infoBox:false,requestRenderMode:true,maximumRenderTimeChange:Infinity,terrainProvider:new C.EllipsoidTerrainProvider(),contextOptions:{webgl:{alpha:false}},skyBox:false,shouldAnimate:false});}
 catch(e){$('#geoEngineError').hidden=false;$('#geoEngineError').textContent='The globe engine could not initialize. Check Chrome hardware acceleration, then reopen World.';$('#geoStatus').textContent='Globe initialization failed';throw e}
 viewer.resolutionScale=Math.min(1,1.5/(window.devicePixelRatio||1));viewer.scene.backgroundColor=C.Color.fromCssColorString('#07101e');viewer.scene.globe.baseColor=C.Color.fromCssColorString('#22374b');viewer.scene.globe.enableLighting=false;viewer.scene.screenSpaceCameraController.minimumZoomDistance=100;installRenderGovernor(viewer);
 const w={C,root,viewer,api:services.api,dead:false,abort:new AbortController(),layers:new Map(),selected:null,region:'Earth',tracked:null,interval:null,moveTimer:null,load_ms:0,
  viewport(){const p=viewer.camera.positionCartographic;const center=viewer.camera.pickEllipsoid(new C.Cartesian2(viewer.canvas.clientWidth/2,viewer.canvas.clientHeight/2),viewer.scene.globe.ellipsoid);const c=center?C.Cartographic.fromCartesian(center):p;return{latitude:+C.Math.toDegrees(c.latitude).toFixed(4),longitude:+C.Math.toDegrees(c.longitude).toFixed(4),altitude:Math.max(10,Math.min(100000000,p.height)),region:this.region}},
  position(row,date=new Date()){
   if(row.satrec){try{const p=window.satellite.propagate(row.satrec,date);if(!p.position)return null;const g=window.satellite.eciToGeodetic(p.position,window.satellite.gstime(date));row.latitude=window.satellite.degreesLat(g.latitude);row.longitude=window.satellite.degreesLong(g.longitude);row.altitude=g.height*1000}catch{return null}}
   if(!Number.isFinite(row.latitude)||!Number.isFinite(row.longitude))return null;
   return C.Cartesian3.fromDegrees(row.longitude,row.latitude,Math.max(0,row.altitude||0));
  },
  visible(){const list=[];const occluder=new C.EllipsoidalOccluder(viewer.scene.globe.ellipsoid,viewer.camera.positionWC);for(const layer of this.layers.values()){if(!layer.enabled)continue;for(const row of layer.records.values()){const pos=row.entity.position?.getValue(viewer.clock.currentTime);if(!pos||!occluder.isPointVisible(pos))continue;const pt=C.SceneTransforms.worldToWindowCoordinates(viewer.scene,pos);if(pt&&pt.x>=0&&pt.y>=0&&pt.x<=viewer.canvas.clientWidth&&pt.y<=viewer.canvas.clientHeight)list.push(row)}}return list},
  context(){if(this.dead)return{};const visible=this.visible().slice(0,39);if(this.selected&&!visible.some(e=>e.id===this.selected.id))visible.unshift(this.selected);return{viewport:this.viewport(),layers:[...this.layers.values()].filter(l=>l.enabled).map(l=>l.id),selected_id:this.selected?.id||'',visible_ids:visible.map(e=>e.id),satellite_positions:Object.fromEntries(visible.filter(e=>e.layer==='satellites').map(e=>[e.id,[e.latitude,e.longitude,e.altitude]])),observed_at:new Date().toISOString()}},
  renderLayers(){if(this.dead)return;$('#geoLayers').innerHTML=[...this.layers.values()].map(l=>`<label class="geo-layer" style="--layer-color:${COLORS[l.id]}"><input type="checkbox" data-layer="${l.id}" ${l.enabled?'checked':''}><span><b>${esc(l.provider.name)}</b><small>${esc(l.state==='idle'?'Not loaded':label(l.state).toUpperCase())}${l.enabled&&l.state!=='connecting'?` · ${l.records.size} records`:''}</small>${l.enabled?`<small title="${esc(l.detail||l.provider.scope)}">${esc(l.detail||l.provider.scope)}</small><small>${l.at?esc(stamp(l.at)):''} ${l.freshness?'· '+esc(label(l.freshness)):''}</small>`:''}</span></label>`).join('');$('#geoLayers').querySelectorAll('[data-layer]').forEach(b=>b.onchange=()=>this.layers.get(b.dataset.layer).toggle(b.checked));this.updateHud()},
  updateHud(){if(this.dead)return;const v=this.viewport();$('#geoRegion').textContent=this.region;$('#geoCoords').textContent=`${v.latitude.toFixed(3)}°, ${v.longitude.toFixed(3)}° · ${(v.altitude/1000).toFixed(0)} km altitude`;const visible=this.visible();$('#geoCount').textContent=visible.length;const box=$('#geoVisible');if(box.closest('details').open){box.innerHTML=visible.slice(0,40).map(e=>`<button data-entity="${esc(e.id)}"><i style="background:${COLORS[e.layer]}"></i>${esc(e.name)}</button>`).join('')||'<p>No reported objects in the current view.</p>';box.querySelectorAll('[data-entity]').forEach(b=>b.onclick=()=>this.select(this.find(b.dataset.entity)))}},
  find(id){for(const l of this.layers.values())if(l.enabled&&l.records.has(id))return l.records.get(id);return null},
  select(row){if(this.selected?.entity?.label)this.selected.entity.label.show=false;this.selected=row;viewer.selectedEntity=row?.entity;viewer.entities.removeById('world-orbit');
   if(!row){$('#geoSelection').innerHTML='<div class="geo-empty">◎</div><h3>Look closer.</h3><p>Select a visible object, or ask about this area.</p>';return}
   row.entity.label.show=true;const l=this.layers.get(row.layer),meta={...row.metadata};delete meta.image_url;
   $('#geoSelection').innerHTML=`<div class="geo-object-tag" style="color:${COLORS[row.layer]}">${esc(label(row.layer))} · ${esc(l.freshness||l.state)}</div><h3>${esc(row.name)}</h3><p class="geo-source">${esc(row.source)} · ${esc(stamp(row.observed_at))}</p><dl><dt>Coordinates</dt><dd>${row.latitude?.toFixed(4)}, ${row.longitude?.toFixed(4)}</dd><dt>Altitude</dt><dd>${(row.altitude/1000).toFixed(2)} km</dd>${Object.entries(meta).filter(([,v])=>v!==null&&v!==undefined&&v!=='').map(([k,v])=>`<dt>${esc(label(k))}</dt><dd>${esc(v)}</dd>`).join('')}</dl>${row.metadata.image_url?`<img class="geo-camera" src="${esc(row.metadata.image_url)}" alt="Public TfL traffic snapshot" loading="lazy"><p>Public snapshot; capture may be delayed.</p>`:''}${row.url?`<a href="${esc(row.url)}" target="_blank" rel="noopener noreferrer">Open source ↗</a>`:''}<button id="geoFollow">Follow selected object</button>`;
   $('#geoFollow').onclick=()=>this.command({action:'follow_entity',entity_id:row.id});
   if(row.satrec){const orbit=[];for(let i=0;i<=90;i+=2){const p=this.position({...row},new Date(Date.now()+i*60000));if(p)orbit.push(p)}viewer.entities.add({id:'world-orbit',polyline:{positions:orbit,width:1.5,material:C.Color.fromCssColorString('#a7a0ff').withAlpha(.65)}})}
   governorRequestRender('selection');
  },
  async apply(actions){for(const a of actions){if(this.dead)return;
   if(a.action==='fly_to'){viewer.trackedEntity=undefined;this.tracked=null;releaseContinuousRender('follow');this.region=a.region||a.location||'Selected location';viewer.camera.flyTo({destination:C.Cartesian3.fromDegrees(a.longitude,a.latitude,a.altitude||120000),duration:1.4});this.updateHud()}
   else if(a.action==='set_layer')await this.layers.get(a.layer)?.toggle(a.enabled);
   else if(a.action==='search_results')this.showPlaces(a.places);
   else if(a.action==='select_entity'||a.action==='follow_entity'){const row=this.find(a.entity_id);if(!row)throw new Error('That object is no longer in the active layer. Refresh and select it again.');this.select(row);if(a.action==='follow_entity'){this.tracked=row.id;viewer.trackedEntity=row.entity;holdContinuousRender('follow');$('#geoStopFollow').hidden=false}}
   else if(a.action==='stop_following'){viewer.trackedEntity=undefined;this.tracked=null;releaseContinuousRender('follow');$('#geoStopFollow').hidden=true}
   else if(a.action==='reset_camera'){await this.apply([{action:'stop_following'},{action:'fly_to',...HOME}])}
   else if(a.action==='zoom'){const amount=Math.max(100,viewer.camera.positionCartographic.height*.45);a.direction==='out'?viewer.camera.zoomOut(amount):viewer.camera.zoomIn(amount)}
   else if(a.action==='research_queued'){const link=$('#geoResearchLink');link.hidden=false;link.onclick=e=>{e.preventDefault();services.route('research')};$('#geoStatus').textContent='Research queued · continue exploring while it runs'}
   governorRequestRender('world-action');
  }},
  async command(action){try{const out=await this.api('/geo/actions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actions:[action],context:this.context()})});if(!this.dead)$('#geoStatus').textContent=out.results.join(' ');return out}catch(e){if(!this.dead)$('#geoStatus').textContent=e.message;throw e}},
  showPlaces(places){const box=$('#geoPlaces');box.hidden=false;box.innerHTML=places.map((p,i)=>`<button data-place="${i}">${esc(p.name)}</button>`).join('')||'<p>No matching places.</p>';box.querySelectorAll('[data-place]').forEach(b=>b.onclick=()=>{const p=places[Number(b.dataset.place)];box.hidden=true;this.apply([{action:'fly_to',...p,region:p.name}])})},
  async ask(message){if(this.busy)return;this.busy=true;$('#geoPrompt button').disabled=true;$('#geoStatus').textContent='RAVEN is interpreting your view…';$('#geoAnswer').innerHTML=`<p class="geo-user">${esc(message)}</p>`;
   try{const result=await services.chat(message);if(this.dead)return;$('#geoAnswer').insertAdjacentHTML('beforeend',`<p>${esc(result.answer)}</p><small>${esc(result.model)} · ${result.tokens?.total||0} tokens · ${result.latency_ms||0} ms</small>`);$('#geoStatus').textContent='Ready · same conversation as text and voice'}catch(e){if(!this.dead)$('#geoAnswer').insertAdjacentHTML('beforeend',`<p role="alert">${esc(e.message)}</p>`)}finally{this.busy=false;if(!this.dead)$('#geoPrompt button').disabled=false}
  },
  diagnostics(){return{load_ms:this.load_ms,entities:[...this.layers.values()].reduce((n,l)=>n+l.records.size,0),render:getRenderGovernorDiagnostics(),disposed:this.dead}},
  dispose(){if(this.dead)return;this.dead=true;this.abort.abort();clearInterval(this.interval);clearTimeout(this.moveTimer);this.removeMove?.();this.removeSelect?.();this.removeRenderError?.();document.removeEventListener('visibilitychange',this.visibility);for(const l of this.layers.values())l.dispose();viewer.destroy();_resetRenderGovernorForTest();if(window.RavenGeo===this)window.RavenGeo=null;root.classList.remove('geo-active')}
 };
 root.classList.add('geo-active');window.RavenGeo=w;
 const offline=await C.TileMapServiceImageryProvider.fromUrl('/static/vendor/cesium/Assets/Textures/NaturalEarthII');if(w.dead)return w;viewer.imageryLayers.addImageryProvider(offline);viewer.camera.setView({destination:C.Cartesian3.fromDegrees(HOME.longitude,HOME.latitude,HOME.altitude)});
 w.removeSelect=viewer.selectedEntityChanged.addEventListener(e=>{const row=e?w.find(e.id):null;if(row?.id!==w.selected?.id)w.select(row)});
 w.removeRenderError=viewer.scene.renderError.addEventListener(()=>{$('#geoEngineError').hidden=false;$('#geoEngineError').textContent='The graphics engine stopped. Leave World and reopen it to recover.'});
 w.removeMove=viewer.camera.moveEnd.addEventListener(()=>{w.updateHud();clearTimeout(w.moveTimer);w.moveTimer=setTimeout(()=>{for(const id of ['aircraft','military','ships'])w.layers.get(id)?.refresh(true)},800)});
 $('#geoVisible').closest('details').ontoggle=()=>w.updateHud();
 $('#geoSearch').onsubmit=async e=>{e.preventDefault();const b=$('#geoSearch button');b.disabled=true;try{await w.command({action:'search',location:$('#geoLocation').value})}finally{if(!w.dead)b.disabled=false}};
 $('#geoPrompt').onsubmit=e=>{e.preventDefault();const message=$('#geoMessage').value;$('#geoMessage').value='';w.ask(message)};
 $('#geoHome').onclick=()=>w.command({action:'reset_camera'});$('#geoZoomIn').onclick=()=>w.command({action:'zoom',direction:'in'});$('#geoZoomOut').onclick=()=>w.command({action:'zoom',direction:'out'});
 $('#geoAsk').onclick=()=>w.ask('What am I looking at?');$('#geoResearch').onclick=()=>w.command({action:'research'});$('#geoRemember').onclick=()=>w.command({action:'remember'});$('#geoStopFollow').onclick=()=>w.command({action:'stop_following'});
 $('#geoPalette').onclick=()=>document.dispatchEvent(new KeyboardEvent('keydown',{key:'k',ctrlKey:true}));
 $('#geoVoice').onclick=()=>services.voice();
 $('#geoBasemap').onchange=async e=>{const mode=e.target.value;try{const provider=mode==='earth'?await C.TileMapServiceImageryProvider.fromUrl('/static/vendor/cesium/Assets/Textures/NaturalEarthII'):new C.UrlTemplateImageryProvider({url:'https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',credit:new C.Credit('Esri, Maxar, Earthstar Geographics, and the GIS User Community',true),maximumLevel:17});if(w.dead)return;viewer.imageryLayers.removeAll();viewer.imageryLayers.addImageryProvider(provider);governorRequestRender('basemap')}catch{$('#geoStatus').textContent='Imagery unavailable. Earth remains usable.'}};
 w.visibility=()=>{if(document.hidden){releaseContinuousRender('follow')}else if(w.tracked)holdContinuousRender('follow')};document.addEventListener('visibilitychange',w.visibility);
 const providers=await w.api('/geo/providers',{signal:w.abort.signal});if(w.dead)return w;
 for(const p of providers.layers)w.layers.set(p.id,new WorldLayer(w,p));
 $('#geoCredits').innerHTML=providers.layers.map(p=>`<p><a href="${esc(p.url)}" target="_blank" rel="noopener noreferrer">${esc(p.credit)}</a></p>`).join('');
 w.renderLayers();w.load_ms=Math.round(performance.now()-started);$('#geoStatus').textContent=`Globe ready · ${w.load_ms} ms initialization`;
 w.layers.get('earthquakes').toggle(true);
 w.interval=setInterval(()=>{if(w.dead||document.hidden)return;for(const l of w.layers.values()){l.refresh();if(l.id==='satellites'&&l.enabled){for(const row of l.records.values()){const pos=w.position(row);if(pos)row.entity.position=pos}governorRequestRender('sgp4-tick')}}if(w.tracked){const current=w.find(w.tracked);if(current)viewer.trackedEntity=current.entity}w.updateHud()},3000);
 return w;
}
