"""Compile explicit scene data to safe, seekable HyperFrames HTML."""
from html import escape
import json
from pathlib import Path


def e(text):
    return escape(str(text))


def card():
    return '<div class="hero-card"><div class="card-symbol">↗</div><div class="card-name">DESIGN<br>IN MOTION</div><div class="card-bottom">CSS / INTERACTION <span>01</span></div></div>'


def visual(scene, topic):
    kind = scene["scene_type"]
    if kind in {"title", "tilt_card", "perspective"}:
        return ('<div class="demo-plane"><div class="plane-grid"></div>' + card() +
                '<div class="axis axis-x"></div><div class="axis axis-y"></div></div>'
                '<svg class="cursor" width="64" height="76" viewBox="0 0 64 76"><path d="M8 5 L8 59 L23 45 L36 68 L48 61 L35 39 L56 37 Z" fill="#F4F7FC" stroke="#080D16" stroke-width="4"/></svg>'
                '<div class="state state-a">БЕЗ НАВЕДЕНИЯ</div><div class="state state-b">:hover → НАКЛОН</div><div class="state state-c">КУРСОР УШЁЛ → ВОЗВРАТ</div>')
    if kind == "code":
        code = scene.get("code", topic.get("code", ""))
        lines = ''.join(f'<div class="code-line"><span class="line-number">{i+1:02}</span><span class="code-text">{e(line) or " "}</span></div>' for i, line in enumerate(code.splitlines()))
        return '<div class="editor"><div class="editor-bar"><i></i><i></i><i></i><span> ' + e(scene.get("filename", "styles.css")) + '</span></div><div class="code-lines">' + lines + '</div></div>'
    if kind == "gradient":
        return '<div class="gradient-card"><div class="gradient-ring"></div><div class="gradient-face"><div class="angle-value">0° → 360°</div><div>ТИП: &lt;angle&gt;</div></div></div><div class="state state-a">--angle → conic-gradient</div>'
    if kind == "bento":
        return '<div class="bento-grid" data-layout-allow-occlusion="intentional-card-expansion"><div class="tile active-tile"><strong>01</strong><span>Открыть проект ↗</span><div class="expanded-copy">Детали проекта</div></div><div class="tile sibling">02</div><div class="tile sibling">03</div><div class="tile sibling">04</div></div><svg class="cursor" width="64" height="76" viewBox="0 0 64 76"><path d="M8 5 L8 59 L23 45 L36 68 L48 61 L35 39 L56 37 Z" fill="white" stroke="#080D16" stroke-width="4"/></svg><div class="state state-a">КЛИК → НОВОЕ СОСТОЯНИЕ</div>'
    if kind == "spotlight":
        return '<div class="spot-card"><div class="spot-glow"></div><div class="spot-copy"><span>POINTER / LIGHT</span><strong>Свет следует<br>за курсором</strong><small>--x · --y → radial-gradient</small></div></div><svg class="cursor" width="64" height="76" viewBox="0 0 64 76"><path d="M8 5 L8 59 L23 45 L36 68 L48 61 L35 39 L56 37 Z" fill="white" stroke="#080D16" stroke-width="4"/></svg>'
    if kind == "skeleton":
        return '<div class="loading-card"><div class="placeholder"><div class="skeleton-avatar"></div><div class="skeleton-line"></div><div class="skeleton-line short"></div><div class="skeleton-line"></div></div><div class="loaded"><div class="loaded-icon">✓</div><strong>Данные готовы</strong><p>Контент занял то же место.</p></div></div><div class="state state-a">ЗАГРУЗКА</div><div class="state state-b">ДАННЫЕ ПРИШЛИ</div>'
    points = scene.get("points", topic.get("key_points", "").splitlines())
    return '<div class="takeaways">' + ''.join(f'<div class="point"><span>{i+1:02}</span><strong>{e(p)}</strong></div>' for i, p in enumerate(points)) + '</div>'


def build_html(board, captions, include_audio=True):
    runtime = (Path(__file__).resolve().parents[1]/'assets/scripted-motion/scene.js').read_text()
    parts = []
    for i, s in enumerate(board["script_timeline"]):
        title = e(s["screen_text"])
        size = 82 if len(s["screen_text"]) < 45 else 68
        parts.append(f'<section id="scene-{i}" class="scene kind-{e(s["scene_type"])}" style="opacity:{1 if i == 0 else 0}">'
                     f'<div class="scene-inner"><div class="eyebrow">{e(s.get("label", f"ШАГ {i+1:02}"))}</div>'
                     f'<h1 style="font-size:{size}px">{title}</h1><div class="stage">{visual(s, board)}</div>'
                     f'<div class="note">{e(s.get("note", ""))}</div></div></section>')
    caption_html = []
    for i, cue in enumerate(captions):
        words = ''.join(f'<span id="cw-{i}-{j}">{e(w["text"])}</span> ' for j, w in enumerate(cue["words"]))
        caption_html.append(f'<div class="caption" id="caption-{i}">{words}</div>')
    duration = board["duration"]
    audio = (f'<audio id="narration" src="public/narration.wav" data-start="0" data-duration="{duration}" data-track-index="10"></audio>'
             f'<audio id="soundtrack" src="public/soundtrack.wav" data-start="0" data-duration="{duration}" data-track-index="11"></audio>') if include_audio else ''
    payload = json.dumps({"scenes": board["script_timeline"], "captions": captions,
                          "outro_start": board["outro_start"], "duration": duration}, ensure_ascii=False).replace('<', '\\u003c')
    return f'''<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><title>{e(board['title'])}</title>
<script src="public/gsap.min.js"></script><link rel="stylesheet" href="public/style.css"></head>
<body><div id="root" data-composition-id="main" data-width="1080" data-height="1920" data-duration="{duration}">
{''.join(parts)}<div class="captions">{''.join(caption_html)}</div>
<div class="chrome"><span>CODE / MOTION</span><span>{e(board.get('language', 'WEB').upper())}</span></div>
<div class="progress-track"><div class="progress"></div></div>
<video id="frog-outro" class="clip frog-outro" src="public/frog.mp4" muted playsinline data-start="{board['outro_start']}" data-duration="{duration-board['outro_start']}" data-track-index="9"></video>
{audio}</div><script id="script-data" type="application/json">{payload}</script>
<script>{runtime}</script></body></html>'''
