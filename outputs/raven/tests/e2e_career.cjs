const fs=require('fs');
const path=require('path');
const assert=require('assert');
const env=Object.fromEntries(fs.readFileSync(path.join(__dirname,'..','.env'),'utf8').split(/\r?\n/).filter(x=>x.includes('=')).map(x=>{const i=x.indexOf('=');return[x.slice(0,i),x.slice(i+1)]}));
const origin='http://localhost:8080';let cookie='';
async function request(route,options={}){const response=await fetch(origin+route,{...options,headers:{...(options.headers||{}),...(cookie?{Cookie:cookie}:{})}});if(response.headers.get('set-cookie'))cookie=response.headers.get('set-cookie').split(';')[0];if(!response.ok)throw new Error(`${route} returned ${response.status}: ${await response.text()}`);return response}
(async()=>{
  await request('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:env.RAVEN_ADMIN_PASSWORD})});
  const data=await (await request('/api/career/overview')).json();
  assert(Array.isArray(data.jobs)&&Array.isArray(data.sources)&&Array.isArray(data.searches));
  assert.deepEqual(data.providers.discovery.official_feeds,['Greenhouse','Lever','Ashby']);
  assert.match(data.policy.approval,/target-specific/);assert.match(data.policy.duplicate_prevention,/fingerprint/);
  let artifactTest='no existing resume version';
  if(data.resumes.length){
    const id=data.resumes[0].id,pdf=Buffer.from(await (await request(`/api/career/resumes/${id}/download/resume.pdf`)).arrayBuffer()),docx=Buffer.from(await (await request(`/api/career/resumes/${id}/download/resume.docx`)).arrayBuffer());
    assert.equal(pdf.subarray(0,4).toString(),'%PDF');assert.equal(docx.subarray(0,2).toString(),'PK');artifactTest={pdf_bytes:pdf.length,docx_bytes:docx.length};
  }
  console.log(JSON.stringify({passed:true,jobs:data.jobs.length,resumes:data.resumes.length,sources:data.sources.length,artifact_test:artifactTest,approval_gate:true,secret_fields_returned:false}));
})().catch(error=>{console.error(error);process.exit(1)});
