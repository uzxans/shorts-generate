# Telegram Video Localization Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first testable MVP layer for a Telegram bot that accepts YouTube/Instagram links, enforces free/paid limits, creates video localization jobs, and delegates processing to the existing video pipeline.

**Architecture:** Keep Telegram-specific handlers thin. Put reusable business rules, persistence, and pipeline command building in `telegram_bot/` so they can be tested without Telegram, network, or paid APIs.

**Tech Stack:** Python stdlib, SQLite, `yt-dlp`, `ffmpeg`, existing `localize_video.py`, future `aiogram 3`.

## Global Constraints

- Free tier: max 60 seconds, fixed voice, low priority, suggested 3 videos/day.
- Paid tier: max 3-5 minutes, voice selection enabled, higher priority.
- Supported sources: YouTube and Instagram only.
- Do not run video processing inside Telegram handlers.
- Check duration and quota before paid TTS or expensive work.
- Keep temporary files short-lived and ready for cleanup.

---

### Task 1: Domain Rules

**Files:**
- Create: `telegram_bot/__init__.py`
- Create: `telegram_bot/domain.py`
- Test: `tests/test_telegram_bot_domain.py`

**Interfaces:**
- Produces: `Plan`, `VideoSource`, `ValidationResult`, `detect_source(url: str) -> VideoSource | None`, `validate_request(url: str, plan: Plan, duration_seconds: float, voice: str | None = None) -> ValidationResult`, `allowed_voices(plan: Plan) -> tuple[str, ...]`.

- [x] **Step 1: Write failing tests**

```python
from telegram_bot.domain import Plan, detect_source, validate_request


def test_detects_supported_sources():
    assert detect_source("https://www.youtube.com/watch?v=abc").name == "YOUTUBE"
    assert detect_source("https://youtu.be/abc").name == "YOUTUBE"
    assert detect_source("https://www.instagram.com/reel/abc/").name == "INSTAGRAM"


def test_rejects_unsupported_sources():
    result = validate_request("https://example.com/video", Plan.FREE, 20)
    assert not result.ok
    assert "YouTube или Instagram" in result.message


def test_free_tier_rejects_long_video_and_voice_choice():
    too_long = validate_request("https://youtu.be/abc", Plan.FREE, 61)
    assert not too_long.ok
    assert "60 секунд" in too_long.message

    voice = validate_request("https://youtu.be/abc", Plan.FREE, 20, voice="alena")
    assert not voice.ok
    assert "выбор голоса" in voice.message


def test_paid_tier_allows_voice_and_rejects_over_limit():
    ok = validate_request("https://youtu.be/abc", Plan.PAID, 240, voice="alena")
    assert ok.ok

    too_long = validate_request("https://youtu.be/abc", Plan.PAID, 301)
    assert not too_long.ok
    assert "5 минут" in too_long.message
```

- [x] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m unittest tests/test_telegram_bot_domain.py -v`

- [x] **Step 3: Write minimal implementation**

Implement enums, constants, URL detection, and request validation in `telegram_bot/domain.py`.

- [x] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m unittest tests/test_telegram_bot_domain.py -v`

### Task 2: SQLite Job Storage

**Files:**
- Create: `telegram_bot/storage.py`
- Test: `tests/test_telegram_bot_storage.py`

**Interfaces:**
- Consumes: `Plan`
- Produces: `init_db(path: Path) -> sqlite3.Connection`, `upsert_user(conn, telegram_id: int, plan: Plan = Plan.FREE) -> None`, `get_user_plan(conn, telegram_id: int) -> Plan`, `create_job(conn, telegram_id: int, url: str, source: str, plan: Plan, voice: str | None) -> int`, `get_job(conn, job_id: int) -> dict`, `update_job_status(conn, job_id: int, status: str, message: str = "") -> None`.

- [x] **Step 1: Write failing tests**

```python
from pathlib import Path
from telegram_bot.domain import Plan
from telegram_bot.storage import create_job, get_job, get_user_plan, init_db, update_job_status, upsert_user


def test_user_defaults_to_free_and_can_be_upgraded(tmp_path: Path):
    conn = init_db(tmp_path / "bot.db")
    assert get_user_plan(conn, 1001) == Plan.FREE
    upsert_user(conn, 1001, Plan.PAID)
    assert get_user_plan(conn, 1001) == Plan.PAID


def test_create_and_update_job(tmp_path: Path):
    conn = init_db(tmp_path / "bot.db")
    job_id = create_job(conn, 1001, "https://youtu.be/abc", "youtube", Plan.FREE, None)
    job = get_job(conn, job_id)
    assert job["status"] == "queued"
    assert job["plan"] == "free"
    update_job_status(conn, job_id, "running", "downloading")
    assert get_job(conn, job_id)["status"] == "running"
    assert get_job(conn, job_id)["message"] == "downloading"
```

- [x] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m unittest tests/test_telegram_bot_storage.py -v`

- [x] **Step 3: Write minimal implementation**

Create SQLite tables for `users` and `jobs`, then implement the storage functions.

- [x] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m unittest tests/test_telegram_bot_storage.py -v`

### Task 3: Pipeline Command Builder

**Files:**
- Create: `telegram_bot/pipeline.py`
- Test: `tests/test_telegram_bot_pipeline.py`

**Interfaces:**
- Consumes: `Plan`
- Produces: `build_metadata_command(url: str) -> list[str]`, `build_download_command(url: str, output_template: Path) -> list[str]`, `build_localize_command(input_path: Path, output_path: Path, plan: Plan, voice: str | None = None) -> list[str]`, `select_voice(plan: Plan, requested_voice: str | None) -> str`.

- [x] **Step 1: Write failing tests**

```python
from pathlib import Path
from telegram_bot.domain import Plan
from telegram_bot.pipeline import build_download_command, build_localize_command, build_metadata_command, select_voice


def test_metadata_command_is_safe_and_playlist_free():
    cmd = build_metadata_command("https://youtu.be/abc")
    assert cmd[:3] == ["yt-dlp", "--no-playlist", "--dump-json"]


def test_download_command_merges_to_mp4():
    cmd = build_download_command("https://youtu.be/abc", Path("input/%(id)s.%(ext)s"))
    assert "--merge-output-format" in cmd
    assert "mp4" in cmd
    assert "--print" in cmd


def test_voice_selection_depends_on_plan():
    assert select_voice(Plan.FREE, "alena") == "ermil"
    assert select_voice(Plan.PAID, "alena") == "alena"
    assert select_voice(Plan.PAID, None) == "alena"


def test_localize_command_targets_existing_pipeline():
    cmd = build_localize_command(Path("input/source.mp4"), Path("output/result.mp4"), Plan.PAID, "zahar")
    assert cmd[0].endswith("python")
    assert "localize_video.py" in cmd[1]
    assert "--input" in cmd
    assert "--output" in cmd
    assert "--voice" in cmd
    assert "zahar" in cmd
```

- [x] **Step 2: Run test to verify it fails**

Run: `venv/bin/python -m unittest tests/test_telegram_bot_pipeline.py -v`

- [x] **Step 3: Write minimal implementation**

Build command lists only. Do not run subprocesses inside this module.

- [x] **Step 4: Run test to verify it passes**

Run: `venv/bin/python -m unittest tests/test_telegram_bot_pipeline.py -v`

### Task 4: Next Layer After This Commit

**Files:**
- Create: `telegram_bot/bot_app.py`
- Create: `telegram_bot/worker.py`
- Create: `telegram_bot/settings.py`
- Create: `telegram_bot/README.md`

**Interfaces:**
- Consumes: domain, storage, and pipeline modules from Tasks 1-3.
- Produces: runnable polling bot, worker loop, `.env` settings, deployment checklist.

- [x] Add `aiogram` bot commands: `/start`, `/status`, `/voices`, admin `/grant_paid`.
- [x] Add message handler that creates jobs but never processes video inline.
- [x] Add worker that polls queued jobs, probes metadata, enforces validation, downloads, localizes, and updates statuses.
- [x] Add VDS deployment instructions with systemd services for bot and worker.
