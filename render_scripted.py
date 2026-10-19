#!/usr/bin/env python3
"""Scripted renderer called by the existing shorts/render.py entrypoint."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from core.scripted_audio import media_duration, prepare_music, prepare_narration
from core.scripted_composition import build_html
from core.scripted_timeline import validate_timeline
from tools.remotion_board import prepare_remotion_project, validate_remotion_timeline

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets/scripted-motion'
REMOTION_ENTRY = ROOT / 'remotion/index.ts'
REMOTION_PUBLIC = ROOT / 'public/scripted'


def render_scripted_topic(topic, *, skip_voice=False, max_duration=60, build_only=False, validate_only=False):
    # Validate before any network, dependency bootstrap or legacy rendering.
    board = validate_timeline(topic, media_duration(ROOT/'assets/frog.mp4'), max_duration)
    if validate_only:
        print(f"✓ [{topic['id']}] {len(board['script_timeline'])} сцен, {board['duration']:.2f}с с заставкой")
        return None
    if not REMOTION_ENTRY.is_file():
        raise RuntimeError('Не найден Remotion entrypoint: remotion/index.ts')
    # Hash isolates edited scripts and stops old narration from leaking into new subjects.
    digest = hashlib.sha256(json.dumps(topic, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:12]
    project = ROOT/'videos'/f"scripted-{topic['id']}-{digest}{'-silent' if skip_voice else ''}"
    public = project/'public'
    public.mkdir(parents=True, exist_ok=True)
    for name in ['display.ttf', 'body.ttf', 'mono.ttf']:
        if (ASSETS/name).is_file():
            shutil.copy2(ASSETS/name, public/name)
    captions = []
    if not skip_voice:
        captions = asyncio.run(prepare_narration(board, project, ROOT/'temp/scripted-voice-cache'))
        prepare_music(ROOT/'assets/music.mp3', public/'soundtrack.wav', board['duration'])
    board['captions'] = captions
    validate_remotion_timeline(board, captions)
    digest_media = REMOTION_PUBLIC / digest
    if not skip_voice:
        digest_media.mkdir(parents=True, exist_ok=True)
        shutil.copy2(public / 'narration.wav', digest_media / 'narration.wav')
        shutil.copy2(public / 'soundtrack.wav', digest_media / 'soundtrack.wav')
    (project/'script.json').write_text(json.dumps(board, ensure_ascii=False, indent=2), encoding='utf-8')
    prepare_remotion_project(board, topic, project, skip_voice=skip_voice)
    print(f"  🎬 Сценарный проект: {project}", flush=True)
    if build_only:
        return project
    from render import slugify
    output = ROOT/'output'/f"{topic['id']}_{slugify(topic['title'])}-motion{'-silent' if skip_voice else ''}.mp4"
    output.parent.mkdir(exist_ok=True)
    partial = output.with_suffix('.partial.mp4')
    props = json.dumps({'board': board, 'includeAudio': not skip_voice,
                        'narrationSrc': f'scripted/{digest}/narration.wav' if not skip_voice else None,
                        'soundtrackSrc': f'scripted/{digest}/soundtrack.wav' if not skip_voice else None}, ensure_ascii=False)
    cmd = ['npx', 'remotion', 'render', str(REMOTION_ENTRY), 'ScriptedShort',
           f'--props={props}', '--fps=30', '--concurrency=2', '--output', str(partial)]
    browser = Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
    if browser.is_file():
        cmd.append(f'--browser-executable={browser}')
    subprocess.run(cmd, check=True, cwd=ROOT)
    if abs(media_duration(partial)-board['duration']) > .12:
        raise RuntimeError('Длительность экспорта не совпала со сценарием; результат оставлен как partial')
    partial.replace(output)
    print(f"✅ Готово: {output}", flush=True)
    return output
