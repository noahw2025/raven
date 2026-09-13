const vm=require('node:vm');
const assert=require('node:assert/strict');
(async()=>{
 const page=await fetch('http://localhost:8080/');
 assert.equal(page.headers.get('cache-control'),'no-store');
 const html=await page.text();
 const path=html.match(/src="([^"]*voice_logic[^"]*)"/)[1];
 assert.match(path,/20260903-voicefix1/);
 const response=await fetch('http://localhost:8080'+path);
 assert.equal(response.headers.get('cache-control'),'no-store');
 const context={window:{}};vm.runInNewContext(await response.text(),context);
 assert.equal(typeof context.window.RavenVoice.updateNoiseFloor,'function');
 console.log('PASS: served voice helper exports updateNoiseFloor; HTML/helper cache prevention active.');
})().catch(error=>{console.error(error.message);process.exit(1)});
