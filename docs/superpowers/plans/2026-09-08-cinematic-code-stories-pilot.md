# Cinematic Code Stories Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render topic 60 as a 35–45 second cinematic, faceless Short/Reel with story-driven Git visuals, word-highlighted subtitles, brief frog reactions, and the existing frog CTA.

**Architecture:** Add a separate `render_cinematic.py` entry point and focused `core/cinematic_*` modules. A deterministic storyboard is retimed from Edge TTS metadata, scene renderers produce composable PIL/NumPy frames, and the orchestration layer mixes existing voice/music/CTA assets without changing `render.py`.

**Tech Stack:** Python 3, MoviePy, Pillow, NumPy, Edge TTS, FFmpeg/ffprobe, `unittest`.

**Spec:** `docs/superpowers/specs/2026-09-08-cinematic-code-stories-pilot-design.md`

## Global Constraints

- Output is vertical 1080×1920, 30 FPS, H.264/AAC, `yuv420p`, BT.709, and `+faststart`.
- Target duration is 35–45 seconds; scene boundaries follow the approved voiceover timings.
- The existing `render.py` behavior and existing topic outputs must remain unchanged.
- Screen subtitles use the approved original text; phonetic TTS text must never leak into captions.
- Important content stays inside `x=64..920` and `y=120..1660`; captions stay inside `y=1450..1660`.
- Frog reactions last 0.4–0.8 seconds and the existing red frog CTA remains the final scene.
- No Runway, generative video API, publishing integration, or automatic storyboard generation is added in this pilot.
- The workspace currently has no `.git` directory. Run each listed Git commit only if Git metadata is restored; otherwise record the completed test command and changed files in the task handoff.

## File Map

- Create `core/cinematic_storyboard.py`: immutable storyboard models, approved voiceover, topic-60 shots, and audio-based retiming.
- Create `core/cinematic_subtitles.py`: caption phrase construction, word timing fallback, active-word lookup, and caption drawing.
- Create `core/cinematic_camera.py`: deterministic easing, zoom/pan transforms, and compositing helpers.
- Create `core/cinematic_scenes.py`: cinematic background and topic-60 scene renderers.
- Create `core/cinematic_frog.py`: frog source decoding, reaction transforms, and final CTA frames.
- Create `render_cinematic.py`: CLI, TTS/cache orchestration, video/audio composition, encoding, and audit contact sheet.
- Create `tests/test_cinematic_storyboard.py`: storyboard and retiming tests.
- Create `tests/test_cinematic_subtitles.py`: caption timing, highlighting, and safe-zone tests.
- Create `tests/test_cinematic_camera.py`: easing and camera-boundary tests.
- Create `tests/test_cinematic_scenes.py`: frame shape, safe-zone, and deterministic rendering tests.
- Create `tests/test_cinematic_frog.py`: reaction timing and fallback tests.
- Create `tests/test_render_cinematic.py`: CLI, export settings, and smoke tests.
- Modify `topics.json`: replace topic 60 voiceover with the approved copy while preserving its title, code, demo, key points, and CTA fields.

---

### Task 1: Storyboard model and audio retiming

**Files:**
- Create: `core/cinematic_storyboard.py`
- Create: `tests/test_cinematic_storyboard.py`

**Interfaces:**
- Consumes: Edge TTS metadata shaped as `{"sentences": [{"offset": float, "duration": float, "text": str}], "words": [...]}`.
- Produces: `Shot`, `CinematicStoryboard`, `topic_60_storyboard()`, and `retime_storyboard(storyboard, tts_meta, cta_duration) -> CinematicStoryboard`.

- [ ] **Step 1: Write failing model and validation tests**

```python
# tests/test_cinematic_storyboard.py
import unittest

from core.cinematic_storyboard import (
    APPROVED_TOPIC_60_VOICEOVER,
    retime_storyboard,
    topic_60_storyboard,
)


class CinematicStoryboardTest(unittest.TestCase):
    def test_topic_60_has_seven_ordered_shots(self):
        board = topic_60_storyboard()
        self.assertEqual(len(board.shots), 7)
        self.assertEqual(board.shots[0].kind, "conflict")
        self.assertEqual(board.shots[-1].kind, "cleanup_cta")
        self.assertTrue(all(a.end <= b.start for a, b in zip(board.shots, board.shots[1:])))
        self.assertEqual(board.voiceover, APPROVED_TOPIC_60_VOICEOVER)

    def test_retime_uses_audio_end_and_reserves_cta(self):
        board = topic_60_storyboard()
        meta = {
            "sentences": [
                {"offset": 0.0, "duration": 3.0, "text": "a"},
                {"offset": 3.0, "duration": 2.0, "text": "b"},
                {"offset": 5.0, "duration": 5.0, "text": "c"},
                {"offset": 10.0, "duration": 3.0, "text": "d"},
                {"offset": 13.0, "duration": 2.0, "text": "e"},
                {"offset": 15.0, "duration": 6.0, "text": "f"},
                {"offset": 21.0, "duration": 4.0, "text": "g"},
                {"offset": 25.0, "duration": 3.0, "text": "h"},
                {"offset": 28.0, "duration": 2.0, "text": "i"},
                {"offset": 30.0, "duration": 2.0, "text": "j"},
            ]
        }
        timed = retime_storyboard(board, meta, cta_duration=4.0)
        self.assertAlmostEqual(timed.shots[-1].end, 36.0)
        self.assertTrue(all(shot.duration > 0 for shot in timed.shots))
        self.assertTrue(all(a.end <= b.start for a, b in zip(timed.shots, timed.shots[1:])))

    def test_retime_rejects_audio_outside_pilot_range(self):
        board = topic_60_storyboard()
        meta = {"sentences": [{"offset": 0.0, "duration": 50.0, "text": "too long"}]}
        with self.assertRaisesRegex(ValueError, "35–45"):
            retime_storyboard(board, meta, cta_duration=4.0)
```

- [ ] **Step 2: Run the tests and confirm the missing-module failure**

Run: `python3 -m unittest tests/test_cinematic_storyboard.py -v`

Expected: `ModuleNotFoundError: No module named 'core.cinematic_storyboard'`.

- [ ] **Step 3: Implement immutable storyboard types and approved shots**

```python
# core/cinematic_storyboard.py
from __future__ import annotations

from dataclasses import dataclass, replace


APPROVED_TOPIC_60_VOICEOVER = (
    "Срочный hotfix прилетел, когда твоя фича развалена на десять файлов? "
    "Не прячь всё в stash. "
    "Одна команда: git worktree add ../app-hotfix -b hotfix/login — и Git создаёт рядом вторую рабочую папку. "
    "В первой продолжает жить твоя feature. Во второй — чистая ветка для исправления. "
    "Открываешь два терминала и работаешь параллельно: без switch, без повторной настройки и без страха потерять изменения. "
    "История и Git-объекты у них общие, поэтому это не второй тяжёлый clone. "
    "Только помни: одну ветку нельзя открыть сразу в двух worktree. "
    "После merge удали папку через git worktree remove. "
    "Сохрани — пригодится при следующем «срочно в прод»."
)


@dataclass(frozen=True)
class Shot:
    id: str
    kind: str
    start: float
    end: float
    narration_start: int
    narration_end: int
    accent_words: tuple[str, ...] = ()
    camera: str = "push_in"
    sfx: str | None = None
    frog_reaction: str | None = None

    @property
    def duration(self) -> float:
        return self.end - self.start


@dataclass(frozen=True)
class CinematicStoryboard:
    topic_id: int
    voiceover: str
    shots: tuple[Shot, ...]

    @property
    def duration(self) -> float:
        return self.shots[-1].end if self.shots else 0.0


def topic_60_storyboard() -> CinematicStoryboard:
    specs = (
        ("conflict", "conflict", 0, 3, 0, 1, ("hotfix",), "snap_focus", "alert", None),
        ("chaos", "chaos", 3, 7, 1, 2, ("stash",), "handheld", "whoosh", "panic"),
        ("command", "terminal_command", 7, 14, 2, 3, ("одна", "команда"), "push_in", "keys", None),
        ("split", "split_worktrees", 14, 24, 3, 6, ("вторую", "параллельно"), "pan", "success", "relief"),
        ("history", "shared_history", 24, 32, 6, 7, ("общие",), "orbit", "whoosh", None),
        ("warning", "branch_warning", 32, 38, 7, 8, ("нельзя",), "snap_focus", "warning", None),
        ("cleanup", "cleanup_cta", 38, 45, 8, 10, ("Сохрани",), "pull_back", "bell", None),
    )
    shots = tuple(Shot(*spec) for spec in specs)
    return CinematicStoryboard(60, APPROVED_TOPIC_60_VOICEOVER, shots)
```

Implement `retime_storyboard` by mapping each shot's sentence-index interval onto TTS offsets, reserving the supplied CTA duration after the last spoken sentence. Clamp frog reaction inserts to 0.4–0.8 seconds inside their owning shot rather than creating overlapping shots. Raise `ValueError("cinematic pilot duration must stay within 35–45 seconds")` when the computed total is outside the accepted range.

- [ ] **Step 4: Run storyboard tests**

Run: `python3 -m unittest tests/test_cinematic_storyboard.py -v`

Expected: all three tests pass.

- [ ] **Step 5: Commit the storyboard checkpoint when Git is available**

```bash
git add core/cinematic_storyboard.py tests/test_cinematic_storyboard.py
git commit -m "feat: define cinematic topic storyboard"
```

---

### Task 2: Word-timed dynamic subtitles

**Files:**
- Create: `core/cinematic_subtitles.py`
- Create: `tests/test_cinematic_subtitles.py`

**Interfaces:**
- Consumes: original display text, TTS word/sentence metadata, frame time, and `assets/Roboto-Bold.ttf`.
- Produces: `CaptionWord`, `CaptionCue`, `build_caption_cues(display_text, tts_meta, video_duration) -> tuple[CaptionCue, ...]`, `active_caption(cues, t)`, and `render_caption(cue, t, frame_size) -> tuple[np.ndarray, tuple[int, int]]`.

- [ ] **Step 1: Write failing timing and safe-zone tests**

```python
# tests/test_cinematic_subtitles.py
import unittest

from core.cinematic_subtitles import active_caption, build_caption_cues, render_caption


class CinematicSubtitleTest(unittest.TestCase):
    def setUp(self):
        self.text = "Срочный hotfix прилетел. Не прячь всё в stash."
        self.meta = {
            "words": [
                {"offset": 0.0, "duration": 0.4, "text": "Срочный"},
                {"offset": 0.4, "duration": 0.5, "text": "hotfix"},
                {"offset": 0.9, "duration": 0.6, "text": "прилетел"},
                {"offset": 1.7, "duration": 0.3, "text": "Не"},
                {"offset": 2.0, "duration": 0.5, "text": "прячь"},
                {"offset": 2.5, "duration": 0.3, "text": "всё"},
                {"offset": 2.8, "duration": 0.5, "text": "в"},
                {"offset": 3.3, "duration": 0.5, "text": "stash"},
            ]
        }

    def test_cues_use_two_to_five_words(self):
        cues = build_caption_cues(self.text, self.meta, 4.0)
        self.assertTrue(all(2 <= len(cue.words) <= 5 for cue in cues))
        self.assertEqual(" ".join(w.text for cue in cues for w in cue.words), "Срочный hotfix прилетел Не прячь всё в stash")

    def test_active_word_follows_audio_time(self):
        cues = build_caption_cues(self.text, self.meta, 4.0)
        cue = active_caption(cues, 0.6)
        self.assertIsNotNone(cue)
        self.assertEqual(cue.active_word_at(0.6).text, "hotfix")

    def test_rendered_caption_stays_inside_safe_zone(self):
        cue = build_caption_cues(self.text, self.meta, 4.0)[0]
        rgba, (x, y) = render_caption(cue, 0.6, (1080, 1920))
        self.assertGreaterEqual(x, 64)
        self.assertGreaterEqual(y, 1450)
        self.assertLessEqual(x + rgba.shape[1], 920)
        self.assertLessEqual(y + rgba.shape[0], 1660)
```

- [ ] **Step 2: Run tests and confirm the missing-module failure**

Run: `python3 -m unittest tests/test_cinematic_subtitles.py -v`

Expected: `ModuleNotFoundError` for `core.cinematic_subtitles`.

- [ ] **Step 3: Implement cue construction and deterministic fallback**

Define frozen dataclasses with exact fields:

```python
@dataclass(frozen=True)
class CaptionWord:
    text: str
    start: float
    end: float


@dataclass(frozen=True)
class CaptionCue:
    start: float
    end: float
    words: tuple[CaptionWord, ...]

    def active_word_at(self, t: float) -> CaptionWord | None:
        return next((word for word in self.words if word.start <= t < word.end), None)
```

Normalize punctuation only for matching. Preserve the original word spelling in `CaptionWord.text`. If TTS word metadata is absent, distribute word durations inside each sentence using `max(1, len(word.strip(".,!?—:;")))` as the weight. Group words into 2–5 word cues, breaking early at `.`, `?`, `!`, `:`, or `—`.

- [ ] **Step 4: Implement caption drawing**

Render an RGBA pill with Roboto Bold, white inactive words, `#D8B45B` active word, black translucent background, and a 6–10% active-word scale pulse. Measure the final composite before choosing `(x, y)`; center it within `x=64..920` and `y=1450..1660`. Draw each word separately so the active word can scale without shifting the whole line.

- [ ] **Step 5: Run subtitle tests**

Run: `python3 -m unittest tests/test_cinematic_subtitles.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit the subtitle checkpoint when Git is available**

```bash
git add core/cinematic_subtitles.py tests/test_cinematic_subtitles.py
git commit -m "feat: add word-timed cinematic captions"
```

---

### Task 3: Camera and layer composition primitives

**Files:**
- Create: `core/cinematic_camera.py`
- Create: `tests/test_cinematic_camera.py`

**Interfaces:**
- Consumes: `np.ndarray` RGB/RGBA layers and normalized local scene progress.
- Produces: `ease_in_out(t)`, `camera_transform(frame, progress, start_scale, end_scale, start_center, end_center)`, and `composite_rgba(base, overlay, x, y)`.

- [ ] **Step 1: Write failing deterministic camera tests**

```python
# tests/test_cinematic_camera.py
import unittest
import numpy as np

from core.cinematic_camera import camera_transform, composite_rgba, ease_in_out


class CinematicCameraTest(unittest.TestCase):
    def test_easing_has_stable_endpoints(self):
        self.assertEqual(ease_in_out(0.0), 0.0)
        self.assertEqual(ease_in_out(1.0), 1.0)
        self.assertAlmostEqual(ease_in_out(0.5), 0.5)

    def test_camera_transform_preserves_frame_shape(self):
        frame = np.zeros((1920, 1080, 3), dtype=np.uint8)
        out = camera_transform(frame, 0.5, 1.0, 1.08, (540, 960), (600, 900))
        self.assertEqual(out.shape, frame.shape)

    def test_rgba_composite_clips_at_edges(self):
        base = np.zeros((100, 100, 3), dtype=np.uint8)
        overlay = np.full((40, 40, 4), 255, dtype=np.uint8)
        out = composite_rgba(base, overlay, 80, 80)
        self.assertEqual(out.shape, base.shape)
        self.assertTrue(out[99, 99].all())
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `python3 -m unittest tests/test_cinematic_camera.py -v`

Expected: missing-module failure.

- [ ] **Step 3: Implement minimal camera primitives**

Use a clamped smoothstep for easing:

```python
def ease_in_out(t: float) -> float:
    t = min(1.0, max(0.0, t))
    return t * t * (3.0 - 2.0 * t)
```

Use Pillow LANCZOS resizing for `camera_transform`, interpolate scale and center using `ease_in_out`, crop back to the original frame size, and fill any exposed area with the frame's edge pixels. `composite_rgba` must support negative coordinates and overlays extending past any edge.

- [ ] **Step 4: Run camera tests**

Run: `python3 -m unittest tests/test_cinematic_camera.py -v`

Expected: all tests pass.

- [ ] **Step 5: Commit the camera checkpoint when Git is available**

```bash
git add core/cinematic_camera.py tests/test_cinematic_camera.py
git commit -m "feat: add cinematic camera primitives"
```

---

### Task 4: Cinematic scene renderers for topic 60

**Files:**
- Create: `core/cinematic_scenes.py`
- Create: `tests/test_cinematic_scenes.py`

**Interfaces:**
- Consumes: `Shot`, absolute time, font paths, and camera helpers.
- Produces: `CinematicSceneRenderer.render(shot: Shot, t: float) -> np.ndarray` and `CinematicSceneRenderer.content_bounds(shot: Shot) -> tuple[int, int, int, int]`.

- [ ] **Step 1: Write failing renderer contract tests**

```python
# tests/test_cinematic_scenes.py
import unittest
import numpy as np

from core.cinematic_scenes import CinematicSceneRenderer
from core.cinematic_storyboard import topic_60_storyboard


class CinematicSceneRendererTest(unittest.TestCase):
    def setUp(self):
        self.renderer = CinematicSceneRenderer(seed=60)
        self.board = topic_60_storyboard()

    def test_every_scene_returns_full_rgb_frame(self):
        for shot in self.board.shots:
            frame = self.renderer.render(shot, (shot.start + shot.end) / 2)
            self.assertEqual(frame.shape, (1920, 1080, 3))
            self.assertEqual(frame.dtype, np.uint8)

    def test_scene_rendering_is_deterministic(self):
        shot = self.board.shots[2]
        a = self.renderer.render(shot, shot.start + 1.0)
        b = self.renderer.render(shot, shot.start + 1.0)
        self.assertTrue(np.array_equal(a, b))

    def test_primary_content_stays_inside_safe_zone(self):
        for shot in self.board.shots[:-1]:
            x0, y0, x1, y1 = self.renderer.content_bounds(shot)
            self.assertGreaterEqual(x0, 64)
            self.assertGreaterEqual(y0, 120)
            self.assertLessEqual(x1, 920)
            self.assertLessEqual(y1, 1400)
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `python3 -m unittest tests/test_cinematic_scenes.py -v`

Expected: missing-module failure.

- [ ] **Step 3: Implement the shared cinematic canvas**

Create a cached 1080×1920 backdrop with `#10100E` graphite base, a warm `#D8B45B` radial light, subtle deterministic noise from `np.random.default_rng(seed)`, vignette, and a low-opacity desk/grid texture. Load `Roboto-Bold.ttf` for UI labels and `JetBrainsMono-Regular.ttf`/`JetBrainsMono-Bold.ttf` for code.

- [ ] **Step 4: Implement seven scene kinds**

Use one renderer method per exact `Shot.kind`:

```python
_SCENE_METHODS = {
    "conflict": "_render_conflict",
    "chaos": "_render_chaos",
    "terminal_command": "_render_terminal_command",
    "split_worktrees": "_render_split_worktrees",
    "shared_history": "_render_shared_history",
    "branch_warning": "_render_branch_warning",
    "cleanup_cta": "_render_cleanup",
}
```

Required visible states:

- `conflict`: unfinished editor plus `СРОЧНЫЙ HOTFIX` notification and snap focus.
- `chaos`: `stash`, `switch`, `install`, `switch back` tokens collide and scatter.
- `terminal_command`: command appears in three chunks: `git worktree add`, `../app-hotfix`, `-b hotfix/login`; success response appears after 70% progress.
- `split_worktrees`: one folder becomes `app-feature` and `app-hotfix`; each has a branch badge and terminal.
- `shared_history`: both worktrees connect to one animated commit graph.
- `branch_warning`: duplicate branch attempt shows a realistic fatal message and one controlled red pulse.
- `cleanup_cta`: `git worktree remove ../app-hotfix` removes the temporary folder and leaves the clean graph ready for the CTA transition.

Apply camera behavior using the shot's `camera` value. Keep motion amplitude below 8% zoom and 80 pixels pan so code remains readable. Add a visual event marker at least every 2.5 seconds through command chunk reveals, cursor motion, graph-node creation, focus changes, or frog reactions.

- [ ] **Step 5: Run scene tests**

Run: `python3 -m unittest tests/test_cinematic_scenes.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit the scene checkpoint when Git is available**

```bash
git add core/cinematic_scenes.py tests/test_cinematic_scenes.py
git commit -m "feat: render cinematic git worktree scenes"
```

---

### Task 5: Frog reactions and preserved CTA

**Files:**
- Create: `core/cinematic_frog.py`
- Create: `tests/test_cinematic_frog.py`

**Interfaces:**
- Consumes: `assets/frog.mp4`, `assets/fotoavatar.png`, reaction name, progress, and target frame size.
- Produces: `FrogAssets`, `load_frog_assets()`, `render_frog_reaction(assets, reaction, progress) -> np.ndarray | None`, and `render_frog_cta(assets, local_t) -> np.ndarray`.

- [ ] **Step 1: Write failing reaction and fallback tests**

```python
# tests/test_cinematic_frog.py
import unittest
from pathlib import Path

from core.cinematic_frog import load_frog_assets, render_frog_cta, render_frog_reaction


class CinematicFrogTest(unittest.TestCase):
    def test_existing_video_produces_full_size_cta(self):
        assets = load_frog_assets(Path("assets/frog.mp4"), Path("assets/fotoavatar.png"))
        frame = render_frog_cta(assets, 0.5)
        self.assertEqual(frame.shape, (1920, 1080, 3))

    def test_reaction_progress_is_limited_to_zero_one(self):
        assets = load_frog_assets(Path("assets/frog.mp4"), Path("assets/fotoavatar.png"))
        with self.assertRaises(ValueError):
            render_frog_reaction(assets, "panic", 1.1)

    def test_missing_video_falls_back_to_avatar(self):
        assets = load_frog_assets(Path("/tmp/missing-frog.mp4"), Path("assets/fotoavatar.png"))
        frame = render_frog_cta(assets, 0.5)
        self.assertEqual(frame.shape, (1920, 1080, 3))
```

- [ ] **Step 2: Run tests and confirm failure**

Run: `python3 -m unittest tests/test_cinematic_frog.py -v`

Expected: missing-module failure.

- [ ] **Step 3: Decode assets once and implement reaction transforms**

Cache the 24 FPS source frames from `assets/frog.mp4`. For `panic`, crop the frog, apply a damped ±4° rotation and a 1.00→1.08→1.00 scale pulse. For `relief`, use a 1.00→1.05 push-in plus a warm glow. Each function returns an RGBA reaction layer so the caller can composite it without replacing the main scene. If no usable frog source exists, return `None` for a reaction.

- [ ] **Step 4: Preserve the full red CTA**

`render_frog_cta` must fit the existing `frog.mp4` frame into 1080×1920 without cropping the frog or the `ПОДПИШИТЕСЬ` lettering. If video is absent, fit `fotoavatar.png` on the same red backdrop and add `ПОДПИШИТЕСЬ` in Roboto Bold.

- [ ] **Step 5: Run frog tests**

Run: `python3 -m unittest tests/test_cinematic_frog.py -v`

Expected: all tests pass.

- [ ] **Step 6: Commit the frog checkpoint when Git is available**

```bash
git add core/cinematic_frog.py tests/test_cinematic_frog.py
git commit -m "feat: add frog reactions to cinematic shorts"
```

---

### Task 6: CLI orchestration, audio mix, and export

**Files:**
- Create: `render_cinematic.py`
- Create: `tests/test_render_cinematic.py`
- Modify: `topics.json`

**Interfaces:**
- Consumes: `topic_60_storyboard`, scene/caption/frog renderers, `render.generate_voiceover`, `render.build_final_audio`, `assets/music.mp3`, and `assets/click.mp3`.
- Produces: `parse_args`, `load_topic`, `build_cinematic_clip`, `mix_cinematic_audio`, `render_contact_sheet`, `render_topic_60`, and CLI output `output/60_git-worktree-cinematic.mp4`.

- [ ] **Step 1: Update topic 60 copy and write failing data test**

Add this test to `tests/test_render_cinematic.py`:

```python
import json
import unittest
from pathlib import Path

from core.cinematic_storyboard import APPROVED_TOPIC_60_VOICEOVER


class CinematicRenderTest(unittest.TestCase):
    def test_topic_60_uses_approved_voiceover(self):
        data = json.loads(Path("topics.json").read_text(encoding="utf-8"))
        topic = next(item for item in data["topics"] if item["id"] == 60)
        self.assertEqual(topic["voiceover"], APPROVED_TOPIC_60_VOICEOVER)
```

Run: `python3 -m unittest tests/test_render_cinematic.py -v`

Expected: failure showing the old topic-60 voiceover.

Replace only topic 60's `voiceover` string with `APPROVED_TOPIC_60_VOICEOVER`, preserving every other field. Run the same test and expect PASS.

- [ ] **Step 2: Add failing CLI and export-setting tests**

```python
import ast

class CinematicCliTest(unittest.TestCase):
    def test_cli_accepts_only_pilot_topic(self):
        from render_cinematic import parse_args
        self.assertEqual(parse_args(["--topic", "60", "--skip-voice"]).topic, 60)
        with self.assertRaises(SystemExit):
            parse_args(["--topic", "59"])

    def test_export_reuses_high_quality_settings(self):
        module = ast.parse(Path("render_cinematic.py").read_text(encoding="utf-8"))
        source = ast.unparse(module)
        self.assertIn("FINAL_VIDEO_BITRATE", source)
        self.assertIn("FINAL_AUDIO_BITRATE", source)
        self.assertIn("FINAL_FFMPEG_PARAMS", source)
```

Run: `python3 -m unittest tests/test_render_cinematic.py -v`

Expected: missing-module failure for `render_cinematic`.

- [ ] **Step 3: Implement CLI, cache paths, and frame composition**

The CLI must support:

```text
--topic 60
--skip-voice
--no-music
--no-sfx
--contact-sheet
--preview-duration FLOAT
```

Reject any topic other than 60 in argument validation. Cache voice and metadata at `temp/60_cinematic_voice.mp3` and `temp/60_cinematic_voice.json`. Build caption cues from the original approved copy. For each frame time: select the active shot, render the base scene, composite an active frog reaction only within the final 0.4–0.8 seconds of a reaction-bearing shot, composite the caption, and use the full frog CTA during the final CTA segment.

- [ ] **Step 4: Implement restrained SFX and audio mixing**

Reuse `assets/click.mp3` for keys/click accents and generate no new required assets. Place copies at storyboard event times using `AudioFileClip.with_start()` and volume 0.10–0.18. Use the same clip with a small pitch/speed change only if MoviePy provides it without another dependency; otherwise reuse it unchanged. Omit missing optional SFX with one console warning. Mix voice at 1.0, music at 0.10–0.14, and SFX under the voice with `CompositeAudioClip`.

- [ ] **Step 5: Implement final encoding and contact sheet**

Encode with the constants imported from `render.py`:

```python
clip.write_videofile(
    str(output_path),
    fps=30,
    codec="libx264",
    audio_codec="aac",
    bitrate=FINAL_VIDEO_BITRATE,
    audio_bitrate=FINAL_AUDIO_BITRATE,
    preset="medium",
    ffmpeg_params=FINAL_FFMPEG_PARAMS,
    threads=4,
    logger="bar",
)
```

`render_contact_sheet` samples the midpoint of every shot, scales each frame to 216×384, labels it with shot ID and timestamp, and saves `output/60_git-worktree-cinematic-contact-sheet.jpg`.

- [ ] **Step 6: Run CLI/unit tests**

Run: `python3 -m unittest tests/test_render_cinematic.py -v`

Expected: all tests pass without performing a full network TTS call.

- [ ] **Step 7: Commit the orchestration checkpoint when Git is available**

```bash
git add render_cinematic.py topics.json tests/test_render_cinematic.py
git commit -m "feat: add cinematic short renderer"
```

---

### Task 7: Regression suite and silent preview QA

**Files:**
- Modify: `tests/test_render_cinematic.py`
- Generated but not committed: `output/60_git-worktree-cinematic-preview.mp4`
- Generated but not committed: `output/60_git-worktree-cinematic-contact-sheet.jpg`

**Interfaces:**
- Consumes: completed cinematic renderer.
- Produces: a short deterministic preview and reviewable contact sheet before any paid/network-dependent render.

- [ ] **Step 1: Add a low-resolution smoke path**

Add a `build_cinematic_clip(..., size=(270, 480), fps=10)` test seam and this test:

```python
def test_short_silent_preview_renders(self):
    from render_cinematic import build_cinematic_clip
    clip = build_cinematic_clip(skip_voice=True, duration=1.0, size=(270, 480), fps=10)
    frame = clip.get_frame(0.5)
    self.assertEqual(frame.shape, (480, 270, 3))
    clip.close()
```

- [ ] **Step 2: Run the complete automated suite**

Run:

```bash
python3 -m unittest \
  tests/test_cinematic_storyboard.py \
  tests/test_cinematic_subtitles.py \
  tests/test_cinematic_camera.py \
  tests/test_cinematic_scenes.py \
  tests/test_cinematic_frog.py \
  tests/test_render_cinematic.py \
  tests/test_render_export_settings.py \
  tests/test_motion_storyboard.py \
  tests/test_motion_closure.py -v
```

Expected: all tests pass.

- [ ] **Step 3: Render a five-second silent preview and contact sheet**

Run:

```bash
python3 render_cinematic.py --topic 60 --skip-voice --no-music --preview-duration 5 --contact-sheet
```

Expected: preview MP4 and contact sheet are created under `output/` without network access.

- [ ] **Step 4: Inspect the contact sheet**

Verify all seven shot IDs are present, primary objects remain within the safe zone, code is readable at mobile scale, red is limited to conflict/warning/CTA, and frog reactions do not cover captions.

- [ ] **Step 5: Probe the silent preview**

Run:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt:format=duration -of json output/60_git-worktree-cinematic-preview.mp4
```

Expected: H.264 video, 1080×1920, 30/1 FPS, `yuv420p`, and duration close to 5 seconds.

- [ ] **Step 6: Commit the QA checkpoint when Git is available**

```bash
git add tests/test_render_cinematic.py
git commit -m "test: verify cinematic renderer smoke path"
```

---

### Task 8: Final voiced render and acceptance review

**Files:**
- Generated but not committed: `output/60_git-worktree-cinematic.mp4`
- Generated but not committed: `output/60_git-worktree-cinematic-contact-sheet.jpg`

**Interfaces:**
- Consumes: working Edge TTS/network access plus all completed tasks.
- Produces: the final pilot MP4 and visual QA evidence.

- [ ] **Step 1: Render the complete voiced pilot**

Run:

```bash
python3 render_cinematic.py --topic 60 --contact-sheet
```

Expected: Edge TTS is generated or loaded from cache, the total duration is 35–45 seconds, and both MP4 and contact sheet are written under `output/`.

- [ ] **Step 2: Verify encoded media properties**

Run:

```bash
ffprobe -v error -show_entries stream=codec_name,width,height,r_frame_rate,pix_fmt,color_space,color_transfer,color_primaries:format=duration -of json output/60_git-worktree-cinematic.mp4
```

Expected: H.264/AAC streams, 1080×1920, 30 FPS, `yuv420p`, BT.709 tags, and 35–45 second duration.

- [ ] **Step 3: Perform final visual and audio review**

Watch the complete MP4 once with sound and once muted. Confirm: the first conflict is understandable in two seconds; visual events occur at least every 2.5 seconds; every command remains exact; captions use 2–5 words and highlight the spoken word; voice is never masked; frog reactions last 0.4–0.8 seconds; and the existing red frog CTA is intact.

- [ ] **Step 4: Compare against the existing topic-60 render**

Open `output/60_git.mp4` and `output/60_git-worktree-cinematic.mp4` side by side. Record only concrete acceptance issues: unreadable text, stalled visual intervals, incorrect Git behavior, bad subtitle timing, masked voice, or an abrupt frog transition. Fix any acceptance issue with a failing regression test before changing implementation.

- [ ] **Step 5: Run final regression suite after acceptance fixes**

Run the full command from Task 7 Step 2 again.

Expected: all tests pass after any review-driven fixes.

- [ ] **Step 6: Commit final acceptance fixes when Git is available**

```bash
git add core/cinematic_*.py render_cinematic.py topics.json tests/test_cinematic_*.py tests/test_render_cinematic.py
git commit -m "feat: complete cinematic code stories pilot"
```
