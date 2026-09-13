const assert=require('node:assert/strict');
const origin='http://localhost:8080';
async function call(path,options={}){const r=await fetch(origin+'/api'+path,{...options,headers:{Origin:origin,'Content-Type':'application/json',...options.headers}});const data=await r.json();assert(r.ok,`${path}: ${r.status} ${JSON.stringify(data)}`);return data}
(async()=>{
 const job=await call('/social/quick-media',{method:'POST',body:JSON.stringify({kind:'image',prompt:'RAVEN demo test: a luminous futuristic observatory, mint neon, violet sky, cinematic architectural illustration, no text'})});
 console.log(JSON.stringify({queued:job}));
 for(let i=0;i<90;i++){
  const asset=await call('/social/assets/'+job.asset_id+'/status');
  assert.notEqual(asset.status,'failed','Media generation failed');
  if(asset.status==='media_ready'){
   const r=await fetch(origin+'/api/social/assets/'+job.asset_id+'/content');const bytes=await r.arrayBuffer();assert(r.ok&&bytes.byteLength>1000);assert.match(r.headers.get('content-type'),/image/);
   console.log(JSON.stringify({passed:true,asset_id:job.asset_id,bytes:bytes.byteLength,content_type:r.headers.get('content-type')}));return;
  }
  await new Promise(r=>setTimeout(r,2000));
 }
 throw new Error('Media remains queued after three minutes; inspect Content for progress.');
})().catch(e=>{console.error(e.message);process.exitCode=1});
