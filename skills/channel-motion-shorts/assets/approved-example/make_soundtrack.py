"""Original deterministic minimal electronic score, 120 BPM, 54 seconds."""
import numpy as np
import wave
from pathlib import Path
sr=44100; dur=59; out=np.zeros((sr*dur,2),dtype=np.float64)
rng=np.random.default_rng(54)
def add(t,x,pan=0):
 s=int(t*sr); n=min(len(x),len(out)-s)
 if n>0:
  out[s:s+n,0]+=x[:n]*(.75-pan*.25);out[s:s+n,1]+=x[:n]*(.75+pan*.25)
def note(t,f,length=.35,gain=.1,pan=0):
 x=np.arange(int(sr*length))/sr
 env=np.minimum(x/.012,1)*np.exp(-x*8)
 sound=(np.sin(2*np.pi*f*x)+.22*np.sin(2*np.pi*f*2*x))*env*gain
 add(t,sound,pan);add(t+.1875,sound*.18,-pan)
for k in range(118):
 t=k*.5;x=np.arange(int(sr*.25))/sr
 add(t,np.sin(2*np.pi*(49*x+8*(1-np.exp(-x*35))))*np.exp(-x*18)*.22)
 if k%2:
  noise=rng.standard_normal(int(sr*.1)); add(t,noise*np.exp(-np.arange(len(noise))/sr*65)*.035)
 if k%4==0:
  note(t,[55,65.406,49,73.416][(k//16)%4],.8,.11)
for k in range(236):
 t=k*.25
 if k%2==0 or k%8==7:
  f=[220,329.63,440,523.25,293.66,440,587.33,659.25][k%8]
  note(t,f,.45,.045,(-1 if k%4 else 1)*.5)
for t in [4,14,24,34,46]:
 x=np.arange(int(sr*.35))/sr
 add(t,np.sin(2*np.pi*(850*x-650*x*x))*np.exp(-x*14)*.06)
for t,f in [(49,440),(49.2,554.37),(49.4,659.25)]:note(t,f,1.8,.06)
fade=np.minimum(np.arange(len(out))/sr/1.2,1)*np.minimum((len(out)-np.arange(len(out)))/sr/2.5,1)
out=np.tanh(out*1.3)*fade[:,None]
with wave.open(str(Path('public/soundtrack.wav')),'wb') as w:
 w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes((out*32767).astype('<i2').tobytes())
