"""Scene-local TTS with content-addressed caches and sample-exact placement."""
from __future__ import annotations

import asyncio
import json
import subprocess
import wave
from pathlib import Path

import edge_tts

from core.scripted_timeline import fit_voice, voice_cache_key

VOICE = "ru-RU-DmitryNeural"
RATE = "+5%"
SAMPLE_RATE = 44100
LEAD = 0.12
CTA = "Подпишись, чтобы не пропустить новые разборы."


def media_duration(path):
    return float(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries',
        'format=duration', '-of', 'csv=p=0', str(path)], text=True).strip())


async def synthesize(text, cache, voice=VOICE, rate=RATE):
    key = voice_cache_key(text, voice, rate)
    cache.mkdir(parents=True, exist_ok=True)
    audio, meta = cache / f'{key}.mp3', cache / f'{key}.json'
    if audio.is_file() and meta.is_file():
        saved = json.loads(meta.read_text())
        if saved.get('key') == key and saved.get('words') and audio.stat().st_size:
            return audio, saved
    partial = audio.with_suffix('.part.mp3')
    words = []
    try:
        with partial.open('wb') as out:
            async for chunk in edge_tts.Communicate(text, voice, rate=rate, boundary='WordBoundary').stream():
                if chunk['type'] == 'audio':
                    out.write(chunk['data'])
                elif chunk['type'] == 'WordBoundary':
                    words.append({'text': chunk['text'], 'start': chunk['offset']/1e7,
                                  'end': (chunk['offset']+chunk['duration'])/1e7})
        if not words:
            raise RuntimeError('TTS не вернул тайминги слов; субтитры нельзя синхронизировать')
        info = {'key': key, 'text': text, 'voice': voice, 'rate': rate,
                'duration': media_duration(partial), 'words': words}
        partial.replace(audio)
        meta.write_text(json.dumps(info, ensure_ascii=False, indent=2))
        return audio, info
    finally:
        partial.unlink(missing_ok=True)


def align_segment(source, output, duration, slot):
    speed = fit_voice(duration, slot)
    pcm = subprocess.check_output(['ffmpeg', '-v', 'error', '-i', str(source),
        '-af', f'atempo={speed},loudnorm=I=-18:TP=-2:LRA=7',
        '-ar', str(SAMPLE_RATE), '-ac', '1', '-f', 's16le', '-'])
    frames = round(slot * SAMPLE_RATE)
    lead = round(LEAD * SAMPLE_RATE)
    if len(pcm)//2 + lead > frames:
        raise ValueError('Озвучка после выравнивания не помещается; обрезание запрещено')
    with wave.open(str(output), 'wb') as out:
        out.setparams((1, 2, SAMPLE_RATE, 0, 'NONE', 'not compressed'))
        out.writeframes(bytes(lead*2) + pcm + bytes((frames-lead)*2-len(pcm)))
    return speed


def caption_groups(words, start, speed):
    groups, group = [], []
    for word in words:
        text = word['text']
        if group and (len(group) >= 4 or sum(len(w['text'])+1 for w in group) + len(text) > 32):
            groups.append({'start': group[0]['start'], 'end': group[-1]['end'], 'words': group})
            group = []
        group.append({'text': text, 'start': start + LEAD + word['start']/speed,
                      'end': start + LEAD + word['end']/speed})
    if group:
        groups.append({'start': group[0]['start'], 'end': group[-1]['end'], 'words': group})
    return groups


async def prepare_narration(board, project, cache):
    segments = list(board['script_timeline']) + [{'start': board['outro_start'],
                  'end': board['duration'], 'voiceover': CTA}]
    all_pcm, captions, report = bytearray(), [], []
    for i, scene in enumerate(segments):
        source, meta = await synthesize(scene['voiceover'], cache)
        slot = scene['end'] - scene['start']
        aligned = project / 'public' / f'voice-{i+1}.wav'
        try:
            speed = align_segment(source, aligned, meta['duration'], slot)
        except ValueError as exc:
            raise ValueError(f"Сцена {i+1} ({scene['start']}–{scene['end']}с): {exc}") from exc
        with wave.open(str(aligned)) as wav:
            all_pcm.extend(wav.readframes(wav.getnframes()))
        if i < len(segments)-1:
            captions.extend(caption_groups(meta['words'], scene['start'], speed))
        report.append({'scene': i+1, 'start': scene['start'], 'end': scene['end'],
                       'source_duration': meta['duration'], 'speed': speed, 'voiceover': scene['voiceover']})
        print(f"  🎙 Сцена {i+1}: речь {meta['duration']:.2f}с / слот {slot:.2f}с", flush=True)
    with wave.open(str(project/'public'/'narration.wav'), 'wb') as out:
        out.setparams((1, 2, SAMPLE_RATE, 0, 'NONE', 'not compressed'))
        out.writeframes(all_pcm)
    (project/'narration.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return captions


def prepare_music(source, output, duration):
    subprocess.run(['ffmpeg','-y','-v','error','-stream_loop','-1','-i',str(source),
        '-t',str(duration),'-af',f'volume=0.13,afade=t=in:d=0.5,afade=t=out:st={duration-1}:d=1',
        '-ar','44100','-ac','2',str(output)],check=True)
