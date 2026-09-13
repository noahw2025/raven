// Synthetic end-to-end check for the exact WebSocket path used by Chrome.
const response=await fetch('http://127.0.0.1:8090/synthesize',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({text:'Raven, open Spotify and play Good Morning by Kanye West.'})});
if(!response.ok)throw new Error(`TTS failed: ${response.status}`);
const wav=Buffer.from(await response.arrayBuffer());
const rate=wav.readUInt32LE(24),channels=wav.readUInt16LE(22),bits=wav.readUInt16LE(34);
if(bits!==16)throw new Error(`Expected PCM16 WAV, got ${bits}-bit`);
const dataTag=wav.indexOf(Buffer.from('data'));
const length=wav.readUInt32LE(dataTag+4),start=dataTag+8;
const frames=Math.floor(length/(channels*2));
const samples=new Float32Array(frames);
for(let i=0;i<frames;i++){let sum=0;for(let c=0;c<channels;c++)sum+=wav.readInt16LE(start+(i*channels+c)*2);samples[i]=sum/channels;}
const output=new Int16Array(Math.ceil(frames*16000/rate)+32000);
for(let i=0;i<output.length-32000;i++){const p=i*rate/16000,a=Math.floor(p),b=Math.min(a+1,frames-1);output[i]=samples[a]+(samples[b]-samples[a])*(p-a);}
const events=[],started=performance.now();
const ws=new WebSocket('ws://127.0.0.1:8090/stream',{headers:{Origin:'http://localhost:8080'}});
await new Promise((resolve,reject)=>{ws.onopen=resolve;ws.onerror=reject;});
ws.onmessage=event=>events.push(JSON.parse(event.data));
await new Promise(resolve=>setTimeout(resolve,100));
for(let i=0;i<output.length&&!events.some(e=>e.type==='final');i+=512){ws.send(output.slice(i,i+512));await new Promise(resolve=>setTimeout(resolve,32));}
for(let i=0;i<100&&!events.some(e=>e.type==='final');i++)await new Promise(resolve=>setTimeout(resolve,100));
ws.close();
const ready=events.find(e=>e.type==='ready'),final=events.find(e=>e.type==='final');
if(!ready||ready.pipeline?.stt?.engine!=='parakeet-realtime-eou')throw new Error(`Parakeet stream did not become ready: ${JSON.stringify(events.slice(0,3))}`);
if(!final?.text)throw new Error(`No final transcript: ${JSON.stringify(events.slice(-5))}`);
if(!/open spotify.*play good morning/i.test(final.text))throw new Error('The complete command was not captured: '+final.text);
console.log(JSON.stringify({ready:ready.pipeline.stt,partial_count:events.filter(e=>e.type==='partial').length,final,wall_ms:Math.round(performance.now()-started)},null,2));
