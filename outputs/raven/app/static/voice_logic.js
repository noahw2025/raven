(function(root){
  const logic={
    updateNoiseFloor:(floor,level)=>Math.max(.006,Math.min(.018,Number(level)<Number(floor)*1.5?Number(floor)*.95+Number(level)*.05:Number(floor))),
    playAudio:audio=>new Promise((resolve,reject)=>{
      let settled=false;
      const finish=(interrupted,error)=>{if(settled)return;settled=true;audio.onended=null;audio.onpause=null;audio.onerror=null;error?reject(error):resolve({interrupted})};
      audio.onended=()=>finish(false);
      audio.onpause=()=>finish(!audio.ended);
      audio.onerror=()=>finish(true,new Error('Audio playback failed'));
      audio.play().catch(error=>finish(true,error));
    }),
    hasWakePhrase:text=>/\barise\b/i.test(String(text||'')),
    wakeGreeting:(name='Noah')=>`Good day, ${String(name||'Noah')}. What can I help you with today?`,
    speechThreshold:noiseFloor=>Math.max(.022,Number(noiseFloor||0)*2.6),
    bargeThreshold:noiseFloor=>Math.max(.055,Number(noiseFloor||0)*3.8),
    isSpeechTurn:({activeFrames=0,speechMs=0,confidence=1,noSpeechProbability=0,text=''})=>activeFrames>=8&&speechMs>=280&&confidence>=.30&&noSpeechProbability<=.72&&String(text).trim().length>0,
    isReliableWake:result=>Boolean(result?.wake_phrase_detected&&Number(result.confidence)>=.45&&Number(result.no_speech_probability)<=.65&&Number(result.duration)>=.30),
    // A fixed one-second timeout clipped natural pauses. Keep short acknowledgements
    // responsive while allowing longer, hesitant turns substantially more room.
    endOfTurnSilenceMs:({activeFrames=0,speechMs=0,elapsedMs=0}={})=>{
      if(speechMs<700||activeFrames<18)return 2600;
      if(elapsedMs>12000||speechMs>6500)return 2100;
      return 2250;
    },
    maxTurnMs:45000,
    bargeInGraceMs:550,
    shouldInterrupt:(levels,noiseFloor,frames=8)=>{
      const threshold=Math.max(.055,Number(noiseFloor||0)*3.8);let hits=0;
      for(const level of levels){hits=level>threshold?hits+1:Math.max(0,hits-1);if(hits>=frames)return true}
      return false;
    },
    sentenceChunks:text=>(String(text||'').match(/[^.!?]+[.!?]+|[^.!?]+$/g)||[String(text||'')]).map(x=>x.trim()).filter(Boolean).slice(0,8)
  };
  if(typeof module!=='undefined'&&module.exports)module.exports=logic;
  root.RavenVoice=logic;
})(typeof window!=='undefined'?window:globalThis);
