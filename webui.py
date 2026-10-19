#!/usr/bin/env python3
from __future__ import annotations

import json
import mimetypes
import os
import subprocess
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / "output"
TOPICS = ROOT / "topics.json"
HOST = "127.0.0.1"
PORT = int(os.environ.get("SHORTS_WEB_PORT", "8787"))

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


HTML = r"""<!doctype html>
<html lang="ru">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Shorts Studio</title>
  <style>
    :root{--bg:#07110f;--panel:#0d1b18;--line:#1f453c;--text:#ecfff8;--muted:#8fb9ad;--a:#36d399;--b:#60a5fa;--bad:#fb7185}
    *{box-sizing:border-box} body{margin:0;background:radial-gradient(circle at 20% 5%,rgba(54,211,153,.20),transparent 30%),linear-gradient(145deg,#06100e,#0b1220 70%);color:var(--text);font-family:ui-sans-serif,system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}
    .wrap{max-width:1180px;margin:0 auto;padding:34px 22px 50px}
    header{display:flex;gap:18px;align-items:flex-end;justify-content:space-between;margin-bottom:28px}
    h1{font-size:44px;line-height:1;margin:0;letter-spacing:.2px}.sub{color:var(--muted);margin-top:8px}
    .grid{display:grid;grid-template-columns:1.05fr .95fr;gap:18px}.card{background:rgba(13,27,24,.82);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 22px 70px rgba(0,0,0,.28)}
    h2{font-size:18px;margin:0 0 14px}.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
    input,select,button{height:42px;border-radius:10px;border:1px solid var(--line);background:#071713;color:var(--text);padding:0 12px;font-size:15px}
    input{min-width:0;flex:1} button{background:linear-gradient(135deg,var(--a),var(--b));color:#04100d;font-weight:800;cursor:pointer;border:0} button.secondary{background:#12261f;color:var(--text);border:1px solid var(--line)}
    .topics{display:grid;gap:8px;max-height:420px;overflow:auto}.topic{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:10px;border:1px solid rgba(54,211,153,.2);border-radius:10px;background:rgba(7,23,19,.65)}
    .topic b{font-size:14px}.topic span{color:var(--muted);font-size:13px}.topic button{height:34px;min-width:82px}
    pre{height:320px;overflow:auto;background:#030806;border:1px solid #17352d;border-radius:12px;padding:14px;color:#b8ffe9;font-size:13px;white-space:pre-wrap}
    .files{display:grid;gap:8px;max-height:250px;overflow:auto}.file{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:9px 10px;background:#071713;border:1px solid rgba(96,165,250,.22);border-radius:10px}
    a{color:#93c5fd;text-decoration:none}.pill{display:inline-flex;align-items:center;gap:6px;padding:8px 12px;border:1px solid var(--line);border-radius:999px;color:var(--muted);font-size:13px}
    @media (max-width:900px){.grid{grid-template-columns:1fr} h1{font-size:34px}}
  </style>
</head>
<body>
<div class="wrap">
  <header>
    <div><h1>Shorts Studio</h1><div class="sub">Рендер шортсов, локализация YouTube и быстрый доступ к результатам.</div></div>
    <div class="pill" id="status">idle</div>
  </header>
  <div class="grid">
    <section class="card">
      <h2>Topics</h2>
      <div class="row" style="margin-bottom:12px">
        <input id="filter" placeholder="поиск по теме или id">
        <select id="maxDuration"><option value="60">до 60 сек</option><option value="0">без лимита</option><option value="45">до 45 сек</option><option value="30">до 30 сек</option></select>
        <button class="secondary" onclick="loadTopics()">обновить</button>
      </div>
      <div class="topics" id="topics"></div>
    </section>
    <section class="card">
      <h2>YouTube video → русский</h2>
      <div class="row">
        <input id="url" placeholder="https://www.youtube.com/shorts/...">
        <select id="voice"><option>alena</option><option>oksana</option><option>ermil</option><option>zahar</option></select>
        <button onclick="localize()">video</button>
      </div>
      <div class="row" style="margin-top:12px"><button class="secondary" onclick="testYandex()">test yandex</button><button class="secondary" onclick="loadOutputs()">outputs</button></div>
      <h2 style="margin-top:20px">Log</h2>
      <pre id="log"></pre>
    </section>
    <section class="card">
      <h2>Output</h2>
      <div class="files" id="outputs"></div>
    </section>
    <section class="card">
      <h2>Команды</h2>
      <pre style="height:250px">shorts 31
shorts 31 --max-duration 0
video https://www.youtube.com/shorts/Tn0FtbiHnvw
video config
video test-yandex</pre>
    </section>
  </div>
</div>
<script>
let topics=[], currentJob=null, timer=null;
const $=id=>document.getElementById(id);
async function api(path, opts){ const r=await fetch(path, opts); if(!r.ok) throw new Error(await r.text()); return r.json(); }
async function loadTopics(){ topics=(await api('/api/topics')).topics; renderTopics(); }
function renderTopics(){ const q=$('filter').value.toLowerCase(); $('topics').innerHTML=topics.filter(t=>(String(t.id)+' '+t.title).toLowerCase().includes(q)).map(t=>`<div class="topic"><div><b>${t.id}. ${esc(t.title)}</b><br><span>${esc(t.language||'')}</span></div><button onclick="render(${t.id})">render</button></div>`).join(''); }
async function render(id){ startJob(await api('/api/render',{method:'POST',body:JSON.stringify({id,max_duration:Number($('maxDuration').value)})})); }
async function localize(){ startJob(await api('/api/video',{method:'POST',body:JSON.stringify({url:$('url').value,voice:$('voice').value})})); }
async function testYandex(){ startJob(await api('/api/test-yandex',{method:'POST'})); }
function startJob(j){ currentJob=j.id; $('log').textContent=''; $('status').textContent='running'; clearInterval(timer); timer=setInterval(poll,900); poll(); }
async function poll(){ if(!currentJob) return; const j=await api('/api/job?id='+encodeURIComponent(currentJob)); $('log').textContent=j.log.join(''); $('log').scrollTop=$('log').scrollHeight; $('status').textContent=j.status; if(j.status!=='running'){clearInterval(timer); loadOutputs();} }
async function loadOutputs(){ const files=(await api('/api/outputs')).files; $('outputs').innerHTML=files.map(f=>`<div class="file"><span>${esc(f.name)}<br><small>${f.size_mb} MB</small></span><a href="/file/output/${encodeURIComponent(f.name)}" target="_blank">open</a></div>`).join(''); }
function esc(s){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
$('filter').addEventListener('input', renderTopics);
loadTopics(); loadOutputs();
</script>
</body></html>"""


def new_job(cmd: list[str]) -> dict:
    job_id = str(int(time.time() * 1000))
    job = {"id": job_id, "cmd": cmd, "status": "running", "log": []}
    with JOBS_LOCK:
        JOBS[job_id] = job
    threading.Thread(target=run_job, args=(job,), daemon=True).start()
    return {"id": job_id}


def run_job(job: dict) -> None:
    job["log"].append("$ " + " ".join(cmd_quote(x) for x in job["cmd"]) + "\n")
    try:
        proc = subprocess.Popen(
            job["cmd"],
            cwd=str(ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        assert proc.stdout
        for line in proc.stdout:
            job["log"].append(line)
            job["log"] = job["log"][-900:]
        code = proc.wait()
        job["status"] = "done" if code == 0 else f"failed ({code})"
    except Exception as exc:
        job["log"].append(f"ERROR: {exc}\n")
        job["status"] = "failed"


def cmd_quote(s: str) -> str:
    return s if s.replace("-", "").replace("_", "").replace("/", "").replace(".", "").isalnum() else repr(s)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        return

    def do_GET(self) -> None:
        url = urlparse(self.path)
        if url.path == "/":
            return self.send(200, HTML, "text/html; charset=utf-8")
        if url.path == "/api/topics":
            data = json.loads(TOPICS.read_text(encoding="utf-8"))
            topics = [{"id": t["id"], "title": t["title"], "language": t.get("language", "")} for t in data.get("topics", [])]
            return self.json({"topics": topics})
        if url.path == "/api/outputs":
            files = []
            for p in sorted(OUTPUT.glob("*.mp4"), key=lambda x: x.stat().st_mtime, reverse=True):
                files.append({"name": p.name, "size_mb": round(p.stat().st_size / 1024 / 1024, 2)})
            return self.json({"files": files[:80]})
        if url.path == "/api/job":
            job_id = parse_qs(url.query).get("id", [""])[0]
            with JOBS_LOCK:
                job = JOBS.get(job_id)
            return self.json(job or {"status": "missing", "log": []})
        if url.path.startswith("/file/output/"):
            name = url.path.split("/file/output/", 1)[1]
            path = (OUTPUT / name).resolve()
            if OUTPUT.resolve() not in path.parents or not path.exists():
                return self.send(404, "not found", "text/plain")
            return self.file(path)
        return self.send(404, "not found", "text/plain")

    def do_POST(self) -> None:
        body = self.read_json()
        if self.path == "/api/render":
            topic_id = int(body["id"])
            max_duration = float(body.get("max_duration", 60))
            return self.json(new_job([str(ROOT / "venv/bin/python"), str(ROOT / "render.py"), "--topic", str(topic_id), "--max-duration", str(max_duration)]))
        if self.path == "/api/video":
            url = str(body.get("url", "")).strip()
            voice = str(body.get("voice", "alena")).strip() or "alena"
            if not url:
                return self.send(400, "url is required", "text/plain")
            return self.json(new_job([str(ROOT / "video"), url, "--voice", voice]))
        if self.path == "/api/test-yandex":
            return self.json(new_job([str(ROOT / "video"), "test-yandex"]))
        return self.send(404, "not found", "text/plain")

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length else "{}"
        return json.loads(raw or "{}")

    def json(self, obj: dict) -> None:
        self.send(200, json.dumps(obj, ensure_ascii=False), "application/json; charset=utf-8")

    def file(self, path: Path) -> None:
        ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send(self, code: int, data: str, ctype: str) -> None:
        raw = data.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)


def main() -> None:
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    url = f"http://{HOST}:{PORT}"
    print(f"Shorts Studio: {url}")
    if os.environ.get("SHORTS_WEB_OPEN", "1") != "0":
        threading.Timer(0.5, lambda: webbrowser.open(url)).start()
    httpd.serve_forever()


if __name__ == "__main__":
    main()
