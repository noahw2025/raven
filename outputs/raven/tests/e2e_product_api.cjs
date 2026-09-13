const assert=require('node:assert/strict');
const root='http://localhost:8080/api';
async function call(path,method='GET',body){const r=await fetch(root+path,{method,headers:{'Content-Type':'application/json',Origin:'http://localhost:8080'},body:body?JSON.stringify(body):undefined});if(!r.ok)throw Error(path+' HTTP '+r.status+' '+(await r.text()).slice(0,200));return r.json()}
(async()=>{
 const data={name:'Temporary CRUD acceptance fixture',objective:'Verify local campaign persistence without publishing anything.',audience:'Local automated test only',brand_voice:'Plain',platforms:['instagram']};
 const c=await call('/social/campaigns','POST',data);
 const edited=await call('/social/campaigns/'+c.id,'PUT',{...data,name:'Renamed acceptance fixture',status:'draft'});assert.equal(edited.name,'Renamed acceptance fixture');
 const clone=await call('/social/campaigns/'+c.id+'/duplicate','POST');assert(clone.id!==c.id);
 await call('/social/campaigns/'+clone.id,'DELETE');await call('/social/campaigns/'+c.id,'DELETE');
 const overview=await call('/social/overview');assert(!overview.campaigns.some(x=>[c.id,clone.id].includes(x.id)));
 const research=await call('/research/projects','POST',{title:'Cancellation acceptance fixture',objective:'A synthetic cancellation test; stop before any report is accepted.',depth:1});
 assert((await call('/research/projects/'+research.id+'/cancel','POST')).cancelled);
 assert.equal((await call('/research/projects/'+research.id)).project.status,'cancelled');
 const world=await call('/world');assert.equal(world.items.find(x=>x.id===research.id).group,'archived');
 const healthy=await call('/social/media-health');console.log('Media readiness:',JSON.stringify(healthy));
 assert.equal((await call('/hermes/tools')).connected,true);
 for(const text of ['go to capabilities','zoom in again','only show memories about Spotify']){
  const r=await call('/chat','POST',{message:text,channel:'voice',ui_page:'graph'});assert(r.ui_action);assert.equal(r.tokens.total,0);
 }
 console.log('PASS: campaign persistence/rename/duplicate/delete; research cancellation; world state; Hermes; typed voice actions.');
})().catch(e=>{console.error(e.message);process.exit(1)});
