/* Only this small entry point loads at startup. No globe/vendor work until opened. */
(()=>{
 let dependencies;
 const css=href=>{if(document.querySelector(`link[href="${href}"]`))return;const e=document.createElement('link');e.rel='stylesheet';e.href=href;document.head.append(e)};
 const script=src=>new Promise((resolve,reject)=>{const e=document.createElement('script');e.src=src;e.onload=resolve;e.onerror=()=>{e.remove();reject(new Error('World engine could not load. Please retry.'))};document.head.append(e)});
 window.worldWorkspace=async()=>{
  $('#inspector').dataset.open='false';
  $('#view').innerHTML='<div class="panel" role="status"><div class="eyebrow">RAVEN / WORLD</div><h2>Preparing your view of Earth</h2><p>Loading the globe engine locally. No provider key is sent to your browser.</p></div>';
  if(!dependencies){
   window.CESIUM_BASE_URL='/static/vendor/cesium/';
   css('/static/vendor/cesium/Widgets/widgets.css');css('/static/geospatial.css');
   dependencies=Promise.all([window.Cesium?null:script('/static/vendor/cesium/Cesium.js'),window.satellite?null:script('/static/vendor/satellite.min.js')]).then(()=>import('/static/geospatial.mjs')).catch(e=>{dependencies=null;throw e});
  }
  const module=await dependencies;if(state.page!=='world')return;
  window.RavenGeo?.dispose();
  const mounted=await module.mount($('#view'),{api,escapeHtml,route,voice:()=>startVoice(),chat:async message=>{
    const result=await api('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,conversation_id:state.conversation,channel:'text',ui_page:'world'})});
    setActiveConversation(result.conversation_id);return result;
  }});
  if(state.page!=='world')mounted.dispose();else window.RavenGeo=mounted;
 };
 // One lightweight palette; commands use the same validated actions as voice.
 document.addEventListener('keydown',e=>{
  if(!(e.ctrlKey||e.metaKey)||e.key.toLowerCase()!=='k')return;e.preventDefault();
  if($('#worldPalette')){$('#worldPalette').close();$('#worldPalette').remove();return}
  const d=document.createElement('dialog');d.id='worldPalette';d.className='panel';d.setAttribute('aria-label','RAVEN World commands');
  d.innerHTML='<div class="row"><h2>World commands</h2><button data-close aria-label="Close commands">Close</button></div><p>Explore Earth with RAVEN. Escape closes this menu.</p><form><label>Go to a location<input name="location" placeholder="Atlanta, Tokyo, an airport…" required maxlength="160"></label><button class="primary">Go to location</button></form><div class="stack" data-actions></div><p data-status role="status"></p>';
  const choices=[['Open World',null],['Toggle aircraft','aircraft'],['Toggle satellites','satellites'],['Toggle ships','ships'],['Reset globe','reset']];
  for(const [label,key] of choices){const b=document.createElement('button');b.textContent=label;b.onclick=async()=>{d.close();d.remove();await route('world');if(key)await window.RavenGeo?.command(key==='reset'?{action:'reset_camera'}:{action:'set_layer',layer:key,enabled:!window.RavenGeo.context().layers.includes(key)})};d.querySelector('[data-actions]').append(b)}
  d.querySelector('[data-close]').onclick=()=>{d.close();d.remove()};d.addEventListener('close',()=>d.remove(),{once:true});
  d.querySelector('form').onsubmit=async e=>{e.preventDefault();const location=d.querySelector('input').value;d.close();d.remove();await route('world');await window.RavenGeo?.command({action:'navigate',location})};
  document.body.append(d);d.showModal();d.querySelector('input').focus();
 });
})();
