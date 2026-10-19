# Remotion Scripted Video Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace generic scripted-topic visuals with a Remotion composition whose scene visuals, text, narration, and captions are driven by the same topic script.

**Architecture:** Keep Python as the validated storyboard/TTS preparation boundary. Write a JSON board plus audio assets into a Remotion project directory, then render a single composition with semantic React scene components selected by `scene_type`. Keep the legacy renderers untouched and dispatch only `script_timeline` topics to the new path.

**Tech Stack:** Remotion, React, TypeScript, `@remotion/media`, `@remotion/captions`, Mediabunny, existing Python `edge-tts`/ffmpeg preparation, SVG and frame-driven Remotion animation.

**Spec:** `docs/superpowers/specs/2026-10-01-remotion-scripted-video-design.md`

## Global Constraints

- Render 1080×1920 at 30fps.
- Keep `shorts <topic-id>` as the user-facing command.
- Use `topics.json` and the validated Python board as the source of truth.
- Keep word-level captions tied to the generated narration.
- Do not require an external image-generation API for the first implementation.
- Preserve legacy non-scripted and cinematic renderers.

## Review Focus

- A topic with a `code` scene must display that scene's code and highlights, not a generic code sample; test the scene router and rendered props.
- A topic with a `bento`/layers scene must derive labels from the scene data, not fixed placeholder copy; test topic 57's layer labels.
- Caption cues must remain inside their scene interval after conversion to milliseconds; test boundary and malformed cues.
- Silent rendering must work without narration files while narrated rendering includes the audio track; test both build modes.
- A stale project must not leak into a new topic render; test the generated board fingerprint and output project path.

### Task 1: Add Remotion project dependencies and composition entrypoint

**Files:**
- Modify: `package.json`
- Modify: `package-lock.json`
- Create: `remotion/index.ts`
- Create: `remotion/Root.tsx`
- Create: `remotion/types.ts`
- Test: `tests/test_remotion_project.py`

**Interfaces:**
- Produces a `ScriptedShort` composition accepting a validated board JSON path and media asset names.
- Defines `ScriptedBoard`, `ScriptedScene`, and `CaptionCue` types shared by scene components.

- [ ] **Step 1: Write failing dependency/entrypoint tests**

  Assert that `package.json` includes `remotion`, `react`, `react-dom`, `@remotion/media`, `@remotion/captions`, and `mediabunny`, and that `remotion/index.ts` and `remotion/Root.tsx` exist.

- [ ] **Step 2: Run the focused test and verify it fails**

  Run: `venv/bin/python -m unittest tests/test_remotion_project.py -v`
  Expected: FAIL because the Remotion package and entrypoint do not exist.

- [ ] **Step 3: Install matching Remotion packages and create the entrypoint**

  Use `npx remotion add @remotion/media @remotion/captions` after initializing the package versions, then define a composition with width 1080, height 1920, fps 30, and duration from input props. Keep `index.ts` as the `registerRoot(RemotionRoot)` entrypoint.

- [ ] **Step 4: Run the focused test**

  Run: `venv/bin/python -m unittest tests/test_remotion_project.py -v`
  Expected: PASS.

### Task 2: Build semantic scene components and frame-driven styling

**Files:**
- Create: `remotion/ScriptedShort.tsx`
- Create: `remotion/scenes/SceneShell.tsx`
- Create: `remotion/scenes/TitleScene.tsx`
- Create: `remotion/scenes/CodeScene.tsx`
- Create: `remotion/scenes/LayersScene.tsx`
- Create: `remotion/scenes/GradientScene.tsx`
- Create: `remotion/scenes/TakeawayScene.tsx`
- Create: `remotion/scenes/GenericScene.tsx`
- Create: `remotion/styles.ts`
- Test: `tests/test_remotion_scene_mapping.py`

**Interfaces:**
- `renderScene(scene: ScriptedScene, topic: ScriptedBoard, fps: number): React.ReactNode` routes by `scene_type`.
- Every scene component accepts `{scene, topic}` and uses `useCurrentFrame()` plus `useVideoConfig()` for animation.

- [ ] **Step 1: Write failing mapping tests**

  Test that topic 57 maps its code scene to `CodeScene`, its layer/bento scene to `LayersScene`, and its takeaway scene to `TakeawayScene`; assert that the source code, screen text, and points are present in the generated props.

- [ ] **Step 2: Run tests to verify failure**

  Run: `venv/bin/python -m unittest tests/test_remotion_scene_mapping.py -v`
  Expected: FAIL because the scene router and components are absent.

- [ ] **Step 3: Implement scene components**

  Use inline `interpolate()`/`spring()` values rather than CSS animations. Build semantic visuals from the scene data: layered cards for CSS cascade, animated code lines/highlights, a topic-colored gradient diagram, and checklist points. All scene text must come from `screen_text`, `label`, `code`, `highlights`, `points`, or the topic title; no fixed topic-specific prose.

- [ ] **Step 4: Run mapping tests**

  Run: `venv/bin/python -m unittest tests/test_remotion_scene_mapping.py -v`
  Expected: PASS.

### Task 3: Add Remotion audio, captions, sequencing, and outro

**Files:**
- Modify: `remotion/ScriptedShort.tsx`
- Create: `remotion/CaptionTrack.tsx`
- Create: `remotion/media.ts`
- Modify: `core/scripted_audio.py`
- Test: `tests/test_remotion_timeline.py`

**Interfaces:**
- `toRemotionCaptions(cues: CaptionCue[]): Caption[]` converts seconds to the Remotion caption shape in milliseconds.
- `validateRemotionTimeline(board, captions)` raises a descriptive error for out-of-range scenes or captions.

- [ ] **Step 1: Write failing timeline tests**

  Test exact conversion of a word cue to `{text, startMs, endMs, timestampMs, confidence}` and rejection of a caption that begins before its scene or ends after the board duration.

- [ ] **Step 2: Run tests to verify failure**

  Run: `venv/bin/python -m unittest tests/test_remotion_timeline.py -v`
  Expected: FAIL because conversion and validation are absent.

- [ ] **Step 3: Implement media sequencing**

  Use `Sequence` for each scene, `Audio` from `@remotion/media` for `public/narration.wav` and `public/soundtrack.wav`, and `CaptionTrack` for word highlighting. Keep the frog video only as the explicitly timed outro fallback; use `staticFile()` for copied assets. Make silent mode omit audio layers without changing scene timing.

- [ ] **Step 4: Run timeline tests**

  Run: `venv/bin/python -m unittest tests/test_remotion_timeline.py -v`
  Expected: PASS.

### Task 4: Connect Python build/render flow to Remotion

**Files:**
- Modify: `render_scripted.py`
- Create: `tools/remotion_board.py`
- Modify: `tests/test_scripted_dispatch.py`
- Create: `tests/test_remotion_dispatch.py`

**Interfaces:**
- `prepare_remotion_project(board, topic, project, skip_voice) -> Path` writes `board.json`, assets, and the Remotion project metadata.
- `render_scripted_topic()` invokes `npx remotion render remotion/index.ts ScriptedShort` with the generated project data and existing output naming.

- [ ] **Step 1: Write failing dispatch tests**

  Assert that scripted topics prepare a Remotion project, include the topic digest in the project directory, and no longer invoke `tools/scripted_carve.mjs`.

- [ ] **Step 2: Run tests to verify failure**

  Run: `venv/bin/python -m unittest tests/test_remotion_dispatch.py -v`
  Expected: FAIL because the current implementation calls HyperFrames.

- [ ] **Step 3: Implement the bridge**

  Copy local fonts and generated audio into the project public directory, write the validated board and captions as JSON, run the timeline validator, then call Remotion with `--props` pointing to the project board. Preserve `build_only`, `validate_only`, `skip_voice`, duration checks, and the existing output filename.

- [ ] **Step 4: Run dispatch tests**

  Run: `venv/bin/python -m unittest tests/test_remotion_dispatch.py tests/test_scripted_dispatch.py -v`
  Expected: PASS.

### Task 5: Render topic 57 and verify visual/audio output

**Files:**
- Modify: `docs/scripted-motion.md`
- Create: `tests/test_remotion_render_smoke.py`

- [ ] **Step 1: Add a smoke test for the project command**

  Run the build-only path for topic 57, assert that `board.json`, `narration.wav` (narrated mode), and the Remotion project entrypoint exist, and assert that the board contains the Cascade Layers scene text and code.

- [ ] **Step 2: Run the smoke test before rendering**

  Run: `venv/bin/python -m unittest tests/test_remotion_render_smoke.py -v`
  Expected: PASS after Tasks 1–4.

- [ ] **Step 3: Render a still at each scene boundary**

  Run: `npx remotion still remotion/index.ts ScriptedShort --props=videos/scripted-57-<digest>/board.json --frame=0 --output=/tmp/remotion-57-scene-0.png` and repeat for frames at 5s, 17s, 32s, and 45s. Verify that each still contains the expected scene-specific layout.

- [ ] **Step 4: Render the full narrated video**

  Run: `shorts 57`
  Expected: `output/57_cascade-motion.mp4` is produced with duration matching the board and audio present.

- [ ] **Step 5: Run the complete test suite**

  Run: `venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v` and `npm test -- --runInBand` when the JavaScript test runner is available.
  Expected: all existing tests and new Remotion tests pass.

