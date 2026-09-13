const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const voice=require('../app/static/voice_logic.js');
(async()=>{
  for(const event of ['ended','pause','error']){
    const audio={ended:event==='ended',play:()=>Promise.resolve()};
    const pending=voice.playAudio(audio);
    audio['on'+event]();
    if(event==='error')await assert.rejects(pending,/playback failed/);
    else assert.equal((await pending).interrupted,event==='pause');
    assert.equal(audio.onpause,null);
  }
  await assert.rejects(voice.playAudio({play:()=>Promise.reject(new Error('blocked'))}),/blocked/);
  let floor=.012;for(let i=0;i<120;i++)floor=voice.updateNoiseFloor(floor,.4);
  assert(floor<=.018,'Immediate speech must not poison the noise floor');
  assert(voice.speechThreshold(floor)<.4);
  assert(voice.isSpeechTurn({activeFrames:20,speechMs:600,confidence:.8,noSpeechProbability:.1,text:'play Whitsand Bay'}));
  assert(!voice.isSpeechTurn({activeFrames:2,speechMs:50,confidence:.2,noSpeechProbability:.9,text:'clink'}));
  const source=fs.readFileSync(require.resolve('../app/static/app.js'),'utf8');
  const start=source.slice(source.indexOf('async function startVoiceV2(){'),source.indexOf('startVoice=startVoiceV2;'));
  let wakeStops=0,requests=0,resolveMic,trackStops=0;
  const element={hidden:false,dataset:{},style:{setProperty(){}},classList:{add(){}},textContent:''};
  const context={RavenVoice:voice,state:{voice:null},$:()=>element,stopWakeListener:()=>wakeStops++,requestMicrophone:()=>{requests++;return new Promise(r=>resolveMic=r)},showVoiceFailure:e=>{throw e}};
  vm.createContext(context);vm.runInContext(start+';this.start=startVoiceV2;',context);
  const first=context.start();assert.equal(wakeStops,1);assert(context.state.voice.pending);
  await context.start();assert.equal(requests,1,'Double clicks must not create competing microphone captures');
  context.state.voice=null;resolveMic({getTracks:()=>[{stop:()=>trackStops++}]});await first;
  assert.equal(trackStops,1,'Cancelled pending session must release its microphone');
  context.RavenVoice={};context.state.voice=null;
  await assert.rejects(context.start(),error=>error.code==='stale_client');
  assert.equal(requests,1,'Stale scripts must be detected before microphone capture');
  console.log('Voice lifecycle: 9 checks passed (play/end/interrupt/error, calibration, noise rejection, capture ownership, cancellation).');
})().catch(e=>{console.error(e);process.exit(1)});
