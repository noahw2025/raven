const {chromium}=require(process.env.PLAYWRIGHT_PATH||'C:/Users/ark73/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true,args:['--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1650,height:1100}});const errors=[],requests=[];
 page.on('pageerror',e=>errors.push(e.message));page.on('request',r=>requests.push(r.url()));
 await page.goto('http://localhost:8080/');await page.waitForSelector('.navbtn',{timeout:60000});
 assert(!requests.some(u=>u.includes('/vendor/cesium/')),'globe must remain lazy at boot');
 await page.evaluate(()=>route('world'));await page.waitForFunction(()=>!!window.RavenGeo?.layers?.size,{timeout:60000});
 await page.waitForTimeout(2500);
 const engine=await page.evaluate(()=>({canvas:!!document.querySelector('#geoGlobe canvas'),...RavenGeo.diagnostics()}));assert(engine.canvas);console.log('ENGINE',engine);
 const cmd=actions=>page.evaluate(async actions=>api('/geo/actions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({actions,context:RavenGeo.context()})}),actions);
 await cmd([{action:'fly_to',latitude:33.749,longitude:-84.388,altitude:170000,location:'Atlanta'}]);await page.waitForTimeout(1600);
 let view=await page.evaluate(()=>RavenGeo.context());assert(Math.abs(view.viewport.latitude-33.749)<.1);
 await cmd([{action:'zoom',direction:'out'}]);assert((await page.evaluate(()=>RavenGeo.viewport().altitude))>view.viewport.altitude);
 await cmd([{action:'set_layer',layer:'ships',enabled:true}]);assert.equal(await page.evaluate(()=>RavenGeo.layers.get('ships').state),'api_key_required');
 await cmd([{action:'set_layer',layer:'aircraft',enabled:true},{action:'set_layer',layer:'satellites',enabled:true}]);
 console.log('PROVIDERS',await page.evaluate(()=>[...RavenGeo.layers.values()].filter(l=>l.enabled).map(l=>({layer:l.id,state:l.state,count:l.records.size}))));
 // Return to Earth, select an actual live-feed object, and inspect canonical context.
 await cmd([{action:'reset_camera'}]);await page.waitForTimeout(1600);
 const selected=await page.evaluate(()=>{const w=RavenGeo;const row=w.layers.get('earthquakes').records.values().next().value;if(!row)return null;w.select(row);return row.id});
 assert(selected,'USGS should have a current public earthquake record');
 await page.locator('.geo-visible summary').click();assert.equal((await page.evaluate(()=>RavenGeo.context())).selected_id,selected);
 const facts=await cmd([{action:'get_selected_entity'}]);assert(facts.results[0].includes(selected));
 await page.screenshot({path:'tests/world-integration.png',fullPage:true});
 await page.keyboard.press('Control+k');await page.waitForSelector('#worldPalette[open]');await page.keyboard.press('Escape');
 // Exercise location search against the real provider.
 await cmd([{action:'search',location:'Hartsfield Jackson Atlanta airport'}]);assert(await page.locator('#geoPlaces button').count()>0);
 // Text and voice must traverse exactly the same /api/chat action route.
 for(const channel of ['text','voice']){
  const result=await page.evaluate(async channel=>{const r=await api('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:'Hide aircraft and show satellites.',channel,ui_page:'world',voice_confidence:.95})});return{answer:r.answer,action:r.ui_action,model:r.model,latency:r.latency_ms}},channel);
  console.log('COMMAND',channel,result);assert.equal(result.action?.type,'world_actions');assert(result.action.actions.some(a=>a.action==='set_layer'&&a.layer==='aircraft'&&!a.enabled));
 }
 const before=await page.evaluate(()=>RavenGeo.diagnostics());
 await page.evaluate(()=>route('talk'));assert.equal(await page.evaluate(()=>window.RavenGeo),null);assert.equal(await page.locator('#geoGlobe').count(),0);
 for(const target of ['forge','research','career','studio','graph','tools','command']){await page.evaluate(target=>route(target),target);assert(await page.locator('#view').innerText());}
 await page.evaluate(()=>route('world'));await page.waitForFunction(()=>!!window.RavenGeo?.layers?.size);
 console.log('REENTER',await page.evaluate(()=>RavenGeo.diagnostics()));
 console.log('ERRORS',errors);assert.deepEqual(errors,[]);
 console.log('PASS: lazy globe, navigation, layers, live data, inspector/context, palette, semantic text/voice commands, cleanup, existing routes.');
 await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
