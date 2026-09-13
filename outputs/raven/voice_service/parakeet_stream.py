"""Cache-aware Parakeet streaming ASR adapter for RAVEN.

Derived from NVIDIA-NeMo/labs-Voice-Agent at commit
99cf08c6737537b7987f55e512a0ac8b2ce1f3e1 (Apache-2.0).
RAVEN keeps this small adapter separate from its dialogue/tool router.
"""
import math
import time
from dataclasses import dataclass

import nemo.collections.asr as nemo_asr
import numpy as np
import torch
from nemo.collections.asr.parts.utils.rnnt_utils import Hypothesis
from omegaconf import open_dict

LOG_MEL_ZERO=-16.635

class AudioBuffer:
    def __init__(self,sample_rate:int,seconds:float):
        self.samples=torch.zeros(int(sample_rate*seconds),dtype=torch.float32)
    def reset(self):self.samples.zero_()
    def update(self,audio:np.ndarray):
        incoming=torch.from_numpy(audio) if not isinstance(audio,torch.Tensor) else audio
        size=incoming.shape[0]
        if size>self.samples.shape[0]:raise ValueError("audio frame exceeds streaming buffer")
        self.samples[:-size]=self.samples[size:].clone();self.samples[-size:]=incoming

class FeatureBuffer:
    def __init__(self,sample_rate,buffer_seconds,chunk_seconds,config,device):
        self.sample_rate=sample_rate;self.buffer_seconds=buffer_seconds;self.chunk_seconds=chunk_seconds;self.device=device
        self.sample_buffer=AudioBuffer(sample_rate,buffer_seconds)
        self.feature_length=int(buffer_seconds/config.window_stride);self.chunk_length=int(chunk_seconds/config.window_stride)
        self.features=torch.full([config.features,self.feature_length],LOG_MEL_ZERO,dtype=torch.float32,device=device)
        self.lookback=int(config.window_stride*sample_rate);self.chunk_samples=int(chunk_seconds*sample_rate)
        self.preprocessor=nemo_asr.models.ASRModel.from_config_dict(config).to(device)
    def reset(self):self.sample_buffer.reset();self.features.fill_(LOG_MEL_ZERO)
    def update(self,audio):
        self.sample_buffer.update(audio)
        samples=self.sample_buffer.samples[-(self.lookback+self.chunk_samples):].clone().unsqueeze(0).to(self.device)
        lengths=torch.tensor([samples.shape[1]],device=self.device)
        values,_=self.preprocessor(input_signal=samples,length=lengths);values=values.squeeze()
        extra=values.shape[1]-self.chunk_length-1
        if extra>0:values=values[:,:-extra]
        self.features[:,:-self.chunk_length]=self.features[:,self.chunk_length:].clone()
        self.features[:,-self.chunk_length:]=values[:,-self.chunk_length:].clone()
    def get(self):return self.features.clone()

@dataclass
class StreamResult:
    text:str
    final:bool
    eou_probability:float|None=None
    eob_probability:float|None=None
    processing_ms:float=0

class ParakeetRealtime:
    def __init__(self,model_name="nvidia/parakeet_realtime_eou_120m-v1",device="cuda"):
        self.model_name=model_name;self.device=device;self.eou="<EOU>";self.eob="<EOB>";self.sample_rate=16000;self.chunk_seconds=.08
        self.model=nemo_asr.models.ASRModel.from_pretrained(model_name,map_location=torch.device(device))
        self.model.encoder.set_default_att_context_size(att_context_size=[70,1])
        config=self.model.cfg.decoding
        with open_dict(config):
            config.strategy="greedy";config.compute_timestamps=False;config.preserve_alignments=True
            config.greedy.max_symbols=10;config.fused_batch_size=-1
        self.model.change_decoding_strategy(config);self.model.encoder.set_default_att_context_size(att_context_size=[70,1]);self.model.eval()
        stride=self.model.cfg.preprocessor.window_stride;subsampling=self.model.cfg.encoder.subsampling_factor
        model_chunk=self.model.encoder.streaming_cfg.chunk_size
        if isinstance(model_chunk,list):model_chunk=model_chunk[1]
        pre_cache=self.model.encoder.streaming_cfg.pre_encode_cache_size
        if isinstance(pre_cache,list):pre_cache=pre_cache[1]
        tokens=math.ceil(np.trunc(self.chunk_seconds/stride)/subsampling)
        self.model.encoder.setup_streaming_params(chunk_size=model_chunk//subsampling,shift_size=tokens)
        self.buffer=FeatureBuffer(self.sample_rate,pre_cache*stride+model_chunk*stride,self.chunk_seconds,self.model.cfg.preprocessor,device)
        self.blank=len(self.model.tokenizer.vocab);self.lock=torch.cuda.Stream() if device=="cuda" else None;self.reset()
    def reset(self):
        self.buffer.reset()
        self.cache_channel,self.cache_time,self.cache_length=self.model.encoder.get_initial_cache_state(1)
        self.previous=[Hypothesis(score=0.0,y_sequence=[],dec_state=None,timestamp=[],last_token=None)]
    def _decode(self,tokens):
        ids=[int(token) for token in tokens if int(token)!=self.blank]
        if not ids:return ""
        return "".join(piece.replace("▁"," ") if piece.startswith("▁") else piece for piece in self.model.tokenizer.ids_to_tokens(ids))
    def push(self,pcm16:bytes)->StreamResult:
        started=time.perf_counter();audio=np.frombuffer(pcm16,dtype=np.int16).astype(np.float32)/32768.0;self.buffer.update(audio)
        features=self.buffer.get().unsqueeze(0);length=torch.tensor([features.shape[2]],device=self.device)
        with torch.no_grad(),torch.autocast(device_type="cuda",enabled=self.device=="cuda"):
            encoded,encoded_length,channel,cache_time,cache_length=self.model.encoder.cache_aware_stream_step(processed_signal=features,processed_signal_length=length,cache_last_channel=self.cache_channel,cache_last_time=self.cache_time,cache_last_channel_len=self.cache_length,keep_all_outputs=False,drop_extra_pre_encoded=self.model.encoder.streaming_cfg.drop_extra_pre_encoded)
            best=self.model.decoding.rnnt_decoder_predictions_tensor(encoded,encoded_length,return_hypotheses=True,partial_hypotheses=self.previous)
        self.previous=best;self.cache_channel=channel;self.cache_time=cache_time;self.cache_length=cache_length
        emitted=[];probs=[]
        for timestep in best[0].alignments:
            for logits,token in timestep:
                token=int(token)
                if token!=self.blank:emitted.append(token);probs.append(torch.softmax(logits,dim=-1)[token].item())
        # Alignments only contain the newest encoder step.  The RNNT hypothesis
        # carries the accumulated utterance and must drive partial/final text.
        tokens=[int(token) for token in best[0].y_sequence]
        pieces=self.model.tokenizer.ids_to_tokens(tokens)
        text=self._decode(tokens);final=self.eou in pieces or self.eob in pieces
        emitted_pieces=self.model.tokenizer.ids_to_tokens(emitted)
        eou_prob=probs[emitted_pieces.index(self.eou)] if self.eou in emitted_pieces else None
        eob_prob=probs[emitted_pieces.index(self.eob)] if self.eob in emitted_pieces else None
        clean=text.replace(self.eou,"").replace(self.eob,"").strip()
        if final:self.reset()
        return StreamResult(clean,final,eou_prob,eob_prob,(time.perf_counter()-started)*1000)
