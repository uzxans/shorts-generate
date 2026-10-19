# Motion Full Preview Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a preview video that includes synced voiceover, code scene, background music, and the `assets/frog.mp4` subscribe outro.

**Architecture:** Keep the prototype inside `render_motion.py` and small helpers in `core/motion_closure.py`. Use the existing Yandex SpeechKit helper, MoviePy clips, and final export settings from `render.py`.

**Tech Stack:** Python, MoviePy, PIL, ffmpeg/ffprobe, Yandex SpeechKit.

## Global Constraints

- Use `assets/frog.mp4` as the outro.
- Use `assets/music.mp3` as low-volume background music.
- Keep the output path `output/motion_36_closure.mp4`.
- Keep the first preview focused on topic `36`.
- Do not remove the existing visual style; add code, audio sync, music, and outro.

---

### Task 1: Render Options

**Files:**
- Modify: `render_motion.py`
- Test: `tests/test_render_motion_cli.py`

**Interfaces:**
- Produces: `parse_args(argv)` with defaults `speed="1.08"` and `music_volume=0.10`.

- [ ] Add tests that assert the faster voice speed and music volume defaults.
- [ ] Run `venv/bin/python -m unittest tests/test_render_motion_cli.py` and verify the new assertions fail.
- [ ] Update `parse_args` to expose `--music-volume`, `--no-music`, and faster default `--speed`.
- [ ] Run the same test and verify it passes.

### Task 2: Audio Mix

**Files:**
- Modify: `render_motion.py`
- Test: `tests/test_render_motion_cli.py`

**Interfaces:**
- Produces: `build_motion_audio(voice_path: Path, duration: float, *, music_volume: float, include_music: bool) -> AudioFileClip | CompositeAudioClip`.

- [ ] Add tests that assert background music is included when enabled and omitted when disabled.
- [ ] Run `venv/bin/python -m unittest tests/test_render_motion_cli.py` and verify the tests fail because the helper is missing.
- [ ] Implement `build_motion_audio` using `assets/music.mp3`, looping/trimming to the video duration and mixing below voice.
- [ ] Run the same test and verify it passes.

### Task 3: Full Timeline

**Files:**
- Modify: `core/motion_closure.py`
- Test: `tests/test_motion_closure.py`

**Interfaces:**
- Produces: a visible code scene between the explainer cards and the outro.

- [ ] Add a frame test at `t=31.0` that detects bright code-colored pixels.
- [ ] Run `venv/bin/python -m unittest tests/test_motion_closure.py` and verify it fails.
- [ ] Implement a code panel with highlighted closure lines around `t=24..41`.
- [ ] Run the same test and verify it passes.

### Task 4: Outro Composition

**Files:**
- Modify: `render_motion.py`
- Test: `tests/test_render_motion_cli.py`

**Interfaces:**
- Produces: `build_motion_video(include_outro: bool = True) -> VideoClip` that appends `assets/frog.mp4`.

- [ ] Add a test that `build_motion_video(include_outro=False)` is shorter than `build_motion_video(include_outro=True)`.
- [ ] Run `venv/bin/python -m unittest tests/test_render_motion_cli.py` and verify it fails.
- [ ] Implement `build_motion_video` using `concatenate_videoclips`.
- [ ] Run the same test and verify it passes.

### Task 5: Preview Render

**Files:**
- Modify: `render_motion.py`

**Interfaces:**
- Command: `venv/bin/python render_motion.py --topic 36`

- [ ] Render `output/motion_36_closure.mp4`.
- [ ] Run `ffprobe` to verify video, audio, duration, and frame rate.
- [ ] Open the output for user review.
