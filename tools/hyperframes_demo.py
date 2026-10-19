#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TOPICS_JSON = ROOT / "topics.json"
TEMP = ROOT / "temp"


def format_seconds(seconds: float) -> str:
    text = f"{seconds:.3f}".rstrip("0").rstrip(".")
    return text or "0"


def build_hyperframes_index(demo_html: str, width: int, height: int, duration: float) -> str:
    duration_text = format_seconds(duration)
    root_attrs = (
        f'id="demo" data-composition-id="demo" data-start="0" '
        f'data-duration="{duration_text}" data-width="{width}" data-height="{height}"'
    )
    root_style = f"""
  <style id="hyperframes-demo-root-style">
    html[data-composition-id="demo"] {{
      margin: 0;
      width: {width}px;
      height: {height}px;
      overflow: hidden;
    }}
  </style>
"""
    timeline_script = f"""
  <script id="hyperframes-demo-timeline">
    window.__timelines = window.__timelines || {{}};
    window.__timelines.demo = {{
      _time: 0,
      duration: function() {{ return {duration_text}; }},
      time: function(value) {{
        if (arguments.length) {{
          this._time = Math.max(0, Number(value) || 0);
          return this;
        }}
        return this._time;
      }},
      totalTime: function(value) {{ return this.time(value); }},
      seek: function(value) {{ return this.time(value); }},
      pause: function() {{ return this; }},
      play: function() {{ return this; }},
      timeScale: function() {{ return this; }},
      getChildren: function() {{ return []; }}
    }};
  </script>
"""

    if re.search(r"<html\b", demo_html, flags=re.IGNORECASE):
        html_with_root = re.sub(
            r"<html\b([^>]*)>",
            lambda match: f"<html {root_attrs}{match.group(1)}>",
            demo_html,
            count=1,
            flags=re.IGNORECASE,
        )
        if re.search(r"</head>", html_with_root, flags=re.IGNORECASE):
            html_with_root = re.sub(r"</head>", root_style + "</head>", html_with_root, count=1, flags=re.IGNORECASE)
        else:
            html_with_root = html_with_root.replace("<html ", "<html ", 1).replace(">", "><head>" + root_style + "</head>", 1)
        if re.search(r"</body>", html_with_root, flags=re.IGNORECASE):
            return re.sub(r"</body>", timeline_script + "</body>", html_with_root, count=1, flags=re.IGNORECASE)
        return html_with_root + timeline_script

    return f"""<!doctype html>
<html {root_attrs}>
<head>
  <meta charset="utf-8">
{root_style}
</head>
<body>
  {demo_html}
{timeline_script}
</body>
</html>
"""


def load_topic(path: Path, topic_id: int) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    for topic in data.get("topics", []):
        if topic.get("id") == topic_id:
            return topic
    raise SystemExit(f"topic id {topic_id} not found in {path}")


def write_hyperframes_project(
    topic: dict,
    out_dir: Path,
    width: int,
    height: int,
    duration: float,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "index.html").write_text(
        build_hyperframes_index(topic["demo_html"], width, height, duration),
        encoding="utf-8",
    )
    (out_dir / "meta.json").write_text(
        json.dumps(
            {
                "name": f"topic-{topic['id']}-demo",
                "description": topic.get("title", ""),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return out_dir


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create a HyperFrames demo project from topics.json")
    parser.add_argument("--topic", type=int, required=True)
    parser.add_argument("--topics-json", type=Path, default=TOPICS_JSON)
    parser.add_argument("--out-dir", type=Path)
    parser.add_argument("--width", type=int, default=1080)
    parser.add_argument("--height", type=int, default=760)
    parser.add_argument("--duration", type=float, default=3.0)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    topic = load_topic(args.topics_json, args.topic)
    out_dir = args.out_dir or TEMP / f"hyperframes-topic-{args.topic}"
    project_dir = write_hyperframes_project(topic, out_dir, args.width, args.height, args.duration)
    print(project_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
