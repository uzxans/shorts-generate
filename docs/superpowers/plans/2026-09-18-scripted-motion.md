# Scripted motion implementation plan

> Execute sequentially in this workspace; user approved the design and requested a finished video, keeping `shorts <id>`.

**Goal:** Render timed JSON scenes with explanatory animation, synchronized Dmitry narration, captions, music and the full original frog outro.

**Architecture:** `render.py` routes topics containing `script_timeline` to a separate renderer. A validated timeline is compiled into a seekable HyperFrames composition using a finite set of explicit scene presets. Natural-language visual/motion descriptions remain editorial notes, never silently interpreted as executable instructions.

**Tech stack:** Python, Edge TTS, FFmpeg, HTML/CSS/GSAP, HyperFrames. Existing classic pipeline remains unchanged for other topics. No git repository exists here; no branch/commit operations.

## Tasks

- [ ] Schema + tests: `core/scripted_timeline.py`; validate contiguous finite timestamps, scene/preset names, text, transition duration and total budget including outro. Reject ambiguous prose-only scenes and incomplete narration. Preserve absolute timings.
- [ ] Scene compiler: `core/scripted_composition.py`, `assets/scripted-motion/scene.js`, `style.css`; support title, code, perspective, tilt, gradient, bento, spotlight, skeleton and takeaway scenes. Test generated DOM and deterministic seeking in Chromium, including transition overlap and two distinct demo poses.
- [ ] Audio + orchestration: `core/scripted_audio.py`, `render_scripted.py`; hash voice caches by text/voice/rate, measure each segment, reject overflow rather than truncate, build sample-exact aligned narration and word captions, carve music and render atomically.
- [ ] Integration: route in `render.py`; `shorts 51`, comma-separated batch, all and web UI use the same dispatch. Verify classic route still works. Add validate/build-only options for inexpensive checks.
- [ ] Data: preserve original topics 51–55 in a backup; replace only these with supplied subjects and complete, technically corrected timed scripts. Keep all other topics unchanged. Document supported scene grammar in `docs/scripted-motion.md`.
- [ ] Verification: run focused and regression tests; generate topic 51 through the CLI, inspect frames at every scene and transitions, ffprobe final MP4/audio, verify outro at normal speed and no inline frog.

## Acceptance

## Verification result — 2026-09-18

Implementation completed. Only topic 51 was rendered to MP4, as requested; topics 52–55 were validated and prepared without rendering their videos.

- Final: `output/51_css-motion.mp4`; H.264, 1080×1920, 30 fps, AAC stereo, 56.067 seconds.
- Latest focused Python suite: 14 passed. Broader targeted regression run: 39 passed before the final additional validation test. Browser tests: 2 passed.
- HyperFrames: lint and runtime checks clean, contrast 68/68; seven transient overlap warnings at animated transitions, inspected.
- Contact sheet inspected across all six scenes and two outro frames. Full original frog clip appears only at the end at normal speed.
- Audio: mean −18.9 dB, peak −1.9 dB.
- Remaining unrelated verification limits: broader legacy suite requires missing `temp/motion_36_voice.mp3`; npm audit reports six high-severity dependency findings. No major dependency upgrade was applied as part of this change.

`shorts 51` requires no extra manual step and returns a 1080×1920 / 30fps MP4. New scenarios use their authored seconds, not classic positional heuristics. Invalid timelines/unsupported effects fail with actionable errors before rendering. Final audio is not cut to meet a budget. New topics can reuse registered scenes; new visual mechanisms require a new preset, not magic free-text interpretation.
