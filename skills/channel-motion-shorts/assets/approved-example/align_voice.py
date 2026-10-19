import subprocess,json,wave
from pathlib import Path
lines=json.loads(Path('narration.json').read_text())
chunks=[]
for i,(start,slot,text) in enumerate(lines):
 f=f'public/voice-{i+1}.mp3'
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',f]))
 tempo=max(1,duration/(slot-.3))
 output=f'public/voice-{i+1}-aligned.wav'
 subprocess.run(['ffmpeg','-v','error','-y','-i',f,'-af',f'atempo={tempo},loudnorm=I=-16:TP=-1.5:LRA=7,adelay=100,apad,atrim=duration={slot}','-ar','44100','-ac','1',output],check=True)
 with wave.open(output) as w:
  raw=w.readframes(w.getnframes()); n=int(slot*44100)*2; chunks.append((raw+bytes(n))[:n])
 print(i+1,round(tempo,3),flush=True)
with wave.open('public/narration.wav','wb') as w:
 w.setnchannels(1);w.setsampwidth(2);w.setframerate(44100);w.writeframes(b''.join(chunks))
