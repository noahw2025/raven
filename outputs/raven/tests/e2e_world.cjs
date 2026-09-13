const {chromium}=require('C:/Users/ark73/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true});
 const page=await browser.newPage({viewport:{width:1500,height:1050},reducedMotion:'reduce'}),errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.goto('http://localhost:8080');await page.waitForSelector('.world-station',{timeout:30000});
 assert.equal(await page.locator('.world-station').count(),6);
 await page.waitForFunction(()=>document.querySelector('#worldSync')?.textContent.startsWith('Live records'));
 await page.screenshot({path:path.join(__dirname,'world-home.png'),fullPage:true});
 for(const [station,selector] of [['missions','#operationsList'],['career','#careerOverview'],['studio','#contentBody'],['graph','#graphCanvas'],['hermes','#hermesInventory'],['research','.research-report']]){
  await page.evaluate(()=>route('command'));await page.locator(`[data-station="${station}"]`).click();await page.waitForSelector(selector,{timeout:30000});
  await page.screenshot({path:path.join(__dirname,`world-${station}.png`),fullPage:true});
 }
 await page.evaluate(()=>route('career'));await page.waitForSelector('#careerOverview');
 await page.locator('[data-product-tab="profile"]').click();await page.waitForSelector('#careerProfileForm');
 await page.locator('[data-product-tab="documents"]').click();assert(await page.locator('#careerDocuments').isVisible());
 await page.evaluate(()=>route('studio'));await page.waitForSelector('#contentBody');
 await page.locator('[data-product-tab="media"]').click();
 const newest=await page.evaluate(async()=>{const data=await (await fetch('/api/social/overview')).json();return data.posts.find(p=>p.asset_status==='media_ready')?.asset_id});
 assert(newest,'A verified media artifact should exist');
 const generated=page.locator(`img[src*="${newest}"]`).first();await generated.waitFor({state:'visible',timeout:30000});
 await page.waitForFunction(id=>{const image=document.querySelector(`img[src*="${id}"]`);return image&&image.complete&&image.naturalWidth>0},newest);
 await page.screenshot({path:path.join(__dirname,'world-live-comfyui.png'),fullPage:true});
 for(const tab of ['media','captions','pipeline','schedule','history']){await page.locator(`[data-product-tab="${tab}"]`).click();await page.waitForSelector('#contentBody')}
 await page.evaluate(()=>route('command'));await page.setViewportSize({width:650,height:950});await page.waitForSelector('.world-station');await page.screenshot({path:path.join(__dirname,'world-mobile.png'),fullPage:true});
 assert.deepEqual(errors,[]);console.log('PASS: six world destinations, live state, career tabs, content tabs; no browser exceptions.');
 await browser.close();
})().catch(e=>{console.error(e.message);process.exit(1)});
