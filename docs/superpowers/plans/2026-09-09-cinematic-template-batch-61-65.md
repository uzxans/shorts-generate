# Cinematic Template Batch 61–65 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reusable cinematic Shorts/Reels renderer and produce reviewed previews, then final videos, for topics 61–65.

**Architecture:** Keep storyboard content declarative and separate from rendering. A storyboard registry selects a topic definition, a scene registry delegates to focused visual renderers, and one generalized CLI handles timing, captions, frog outro, previews, contact sheets, TTS, audio, and export.

**Tech Stack:** Python 3.13, unittest, Pillow, NumPy, MoviePy, Edge TTS, FFmpeg/ffprobe.

**Spec:** `docs/superpowers/specs/2026-09-09-cinematic-template-batch-61-65-design.md`

## Global Constraints

- Output is vertical 1080×1920 at 30 FPS with H.264/AAC, `yuv420p`, and `bt709`.
- Narrated content targets 32–40 seconds before the frog outro.
- Meaningful visual change occurs every 1.5–2.5 seconds on average.
- Every story visibly explains the problem, cause, mechanism, result, and one limitation.
- Code and identifiers retain exact spelling; current technical claims are verified against primary official documentation.
- Inline frog reactions are forbidden.
- `assets/frog.mp4` plays once at natural speed as the unobstructed final segment.
- Existing `render.py` behavior must not change.
- Missing optional SFX warns and degrades gracefully; missing mandatory font, voice, or frog outro fails clearly.
- This directory is not currently a Git repository. At each commit step, run the listed `git rev-parse` check; if it still fails, record the tested file set in the execution update instead of attempting a commit.

---

## Package A — Reusable cinematic engine

### Task 1: Storyboard model and topic registry

**Files:**
- Modify: `core/cinematic_storyboard.py`
- Create: `core/cinematic_topics.py`
- Modify: `tests/test_cinematic_storyboard.py`
- Create: `tests/test_cinematic_topics.py`

**Interfaces:**
- Consumes: existing `Shot`, `CinematicStoryboard`, `retime_storyboard(...)`.
- Produces: `get_storyboard(topic_id: int) -> CinematicStoryboard`, `supported_topic_ids() -> tuple[int, ...]`, and data-only `scene_data: Mapping[str, object]` on `Shot`.

- [ ] **Step 1: Write failing tests for generic scene data and registry behavior**

```python
from core.cinematic_storyboard import Shot
from core.cinematic_topics import get_storyboard, supported_topic_ids


def test_shot_carries_scene_specific_data():
    shot = Shot("x", "process_chain", 0, 1, 0, 1, scene_data={"nodes": ("render", "fetch")})
    assert shot.scene_data["nodes"] == ("render", "fetch")


def test_registry_keeps_pilot_and_lists_batch():
    assert supported_topic_ids() == (60, 61, 62, 63, 64, 65)
    assert get_storyboard(60).topic_id == 60


def test_registry_rejects_unknown_topic():
    with unittest.TestCase().assertRaisesRegex(ValueError, "unsupported cinematic topic: 999"):
        get_storyboard(999)
```

- [ ] **Step 2: Run the focused tests and confirm the expected import/signature failures**

Run: `venv/bin/python -m unittest tests/test_cinematic_storyboard.py tests/test_cinematic_topics.py -v`

Expected: FAIL because `core.cinematic_topics` and `Shot.scene_data` do not exist.

- [ ] **Step 3: Extend the immutable model without breaking topic 60**

```python
from dataclasses import dataclass, field
from typing import Mapping

@dataclass(frozen=True)
class Shot:
    # existing fields remain in their current order
    scene_data: Mapping[str, object] = field(default_factory=dict)
```

Move topic selection into `core/cinematic_topics.py`. Keep `topic_60_storyboard()` available as a compatibility wrapper while the registry maps IDs 60–65 to their builders.

- [ ] **Step 4: Add strict storyboard validation**

Add `validate_storyboard(board: CinematicStoryboard) -> None` and test exact failures for: no shots, first shot not starting at `0.0`, gaps/overlaps, non-positive duration, empty narration range, and an unregistered scene kind. Validation must run inside `get_storyboard`.

- [ ] **Step 5: Run focused and pilot tests**

Run: `venv/bin/python -m unittest tests/test_cinematic_storyboard.py tests/test_cinematic_topics.py tests/test_render_cinematic.py -v`

Expected: PASS.

- [ ] **Step 6: Checkpoint**

Run: `git rev-parse --is-inside-work-tree`

If true, commit with `git add core/cinematic_storyboard.py core/cinematic_topics.py tests/test_cinematic_storyboard.py tests/test_cinematic_topics.py && git commit -m "refactor: add cinematic storyboard registry"`. If false, report those four files as Package A / Task 1.

### Task 2: Scene registry and shared drawing primitives

**Files:**
- Modify: `core/cinematic_scenes.py`
- Create: `core/cinematic_scene_registry.py`
- Create: `core/cinematic_primitives.py`
- Modify: `tests/test_cinematic_scenes.py`
- Create: `tests/test_cinematic_scene_registry.py`

**Interfaces:**
- Consumes: `Shot.kind`, `Shot.scene_data`, current `CinematicSceneRenderer.render(shot, t)`.
- Produces: `SceneRenderer = Callable[[ImageDraw.ImageDraw, Shot, float], None]`, `register_scene(kind, renderer)`, `render_scene(kind, draw, shot, progress)`, `registered_scene_kinds()`.

- [ ] **Step 1: Write failing registry tests**

```python
def test_registry_dispatches_scene_by_kind():
    calls = []
    register_scene("unit_scene", lambda draw, shot, progress: calls.append((shot.id, progress)))
    render_scene("unit_scene", object(), sample_shot(kind="unit_scene"), 0.25)
    assert calls == [("sample", 0.25)]


def test_unknown_scene_has_actionable_error():
    with unittest.TestCase().assertRaisesRegex(ValueError, "unknown cinematic scene kind: missing"):
        render_scene("missing", object(), sample_shot(kind="missing"), 0.5)
```

- [ ] **Step 2: Run the new test and confirm failure**

Run: `venv/bin/python -m unittest tests/test_cinematic_scene_registry.py -v`

Expected: FAIL because the registry module does not exist.

- [ ] **Step 3: Implement the minimal registry and move reusable helpers**

Move window, terminal, code, pill, folder, line, arrow, font, and progress helpers from `core/cinematic_scenes.py` into `core/cinematic_primitives.py`. Preserve their current pixel output for topic 60.

```python
_SCENES: dict[str, SceneRenderer] = {}

def register_scene(kind: str, renderer: SceneRenderer) -> None:
    if kind in _SCENES:
        raise ValueError(f"cinematic scene already registered: {kind}")
    _SCENES[kind] = renderer

def render_scene(kind: str, draw, shot: Shot, progress: float) -> None:
    try:
        renderer = _SCENES[kind]
    except KeyError as exc:
        raise ValueError(f"unknown cinematic scene kind: {kind}") from exc
    renderer(draw, shot, progress)
```

- [ ] **Step 4: Route the pilot scenes through the registry**

Register the existing topic-60 kinds (`conflict`, `chaos`, `terminal_command`, `split_worktrees`, `shared_history`, `branch_warning`, `cleanup_cta`). `CinematicSceneRenderer.render(...)` remains the public frame-producing facade.

- [ ] **Step 5: Verify pixel shape, semantic markers, and pilot compatibility**

Run: `venv/bin/python -m unittest tests/test_cinematic_scene_registry.py tests/test_cinematic_scenes.py tests/test_cinematic_camera.py -v`

Expected: PASS; every returned frame remains RGB 1080×1920 and topic-60 explanation markers remain present.

- [ ] **Step 6: Checkpoint**

Run the repository check from Task 1. If Git is available, commit the five files with message `refactor: add cinematic scene registry`; otherwise report them in the checkpoint update.

### Task 3: New explanatory scene families

**Files:**
- Create: `core/cinematic_scene_flow.py`
- Create: `core/cinematic_scene_index.py`
- Create: `core/cinematic_scene_browser.py`
- Create: `core/cinematic_scene_config.py`
- Create: `core/cinematic_scene_css.py`
- Create: `tests/test_cinematic_scene_families.py`

**Interfaces:**
- Consumes: `register_scene`, primitives, and `Shot.scene_data`.
- Produces registered kinds: `problem_ui`, `process_chain`, `code_build`, `before_after`, `data_flow`, `timeline`, `index_tree`, `browser_navigation`, `config_diff`, `css_state_transition`, `warning`, `resolution`.

- [ ] **Step 1: Write parameterized contract tests for every new kind**

```python
CASES = {
    "process_chain": {"nodes": ("render", "effect", "fetch")},
    "index_tree": {"mode": "v7", "keys": ("019a…", "019b…")},
    "browser_navigation": {"url": "/profile", "state": "intercepted"},
    "config_diff": {"before": "types: []", "after": 'types: ["node"]'},
    "css_state_transition": {"from": {"opacity": 0}, "to": {"opacity": 1}},
}

def test_scene_family_changes_visibly_over_time():
    for kind, data in CASES.items():
        early = renderer.render(sample_shot(kind=kind, scene_data=data), 0.1)
        late = renderer.render(sample_shot(kind=kind, scene_data=data), 0.9)
        assert early.shape == (1920, 1080, 3)
        assert numpy.mean(numpy.abs(early.astype(int) - late.astype(int))) > 1.0
```

Also assert required keys produce explicit errors such as `scene index_tree requires scene_data.keys`.

- [ ] **Step 2: Run and confirm unknown-kind failures**

Run: `venv/bin/python -m unittest tests/test_cinematic_scene_families.py -v`

Expected: FAIL because the modules and registrations do not exist.

- [ ] **Step 3: Implement flow scenes**

Implement progressive node activation, arrows, payload movement, and before/after layouts in `core/cinematic_scene_flow.py`. Use progress bands rather than random animation so contact sheets are deterministic.

- [ ] **Step 4: Implement index and timeline scenes**

In `core/cinematic_scene_index.py`, show v4 keys landing across separated tree leaves and v7 keys landing near the newest leaf. Label the visual as index locality, not a guaranteed database benchmark.

- [ ] **Step 5: Implement browser, config, and CSS scenes**

The browser renderer must show navigation start, interception, abort of the previous request, and final page replacement. The config renderer must connect each changed key to a visible diagnostic. The CSS renderer must visibly move from no computed start state to `@starting-style`, then show the reduced-motion branch without animating it.

- [ ] **Step 6: Run family and legacy scene tests**

Run: `venv/bin/python -m unittest tests/test_cinematic_scene_families.py tests/test_cinematic_scenes.py -v`

Expected: PASS.

- [ ] **Step 7: Checkpoint**

Use the Git-or-report checkpoint procedure from Task 1 with commit message `feat: add cinematic explainer scene families`.

### Task 4: Generalize the cinematic CLI and file naming

**Files:**
- Modify: `render_cinematic.py`
- Modify: `tests/test_render_cinematic.py`
- Modify: `tests/test_render_export_settings.py`

**Interfaces:**
- Consumes: `get_storyboard(topic_id)`, `supported_topic_ids()`, existing subtitle/camera/frog/audio functions.
- Produces: `artifact_paths(topic_id: int, slug: str) -> ArtifactPaths`, `build_cinematic_clip(topic_id, ...)`, `render_topic(args) -> Path`.

- [ ] **Step 1: Write failing CLI and path tests**

```python
def test_cli_accepts_supported_batch_topic():
    assert parse_args(["--topic", "65", "--skip-voice"]).topic == 65


def test_paths_are_topic_specific():
    paths = artifact_paths(61, "react-use-suspense")
    assert paths.video.name == "61_react-use-suspense-cinematic.mp4"
    assert paths.voice.name == "61_cinematic_voice.mp3"
    assert paths.contact_sheet.name == "61_react-use-suspense-cinematic-contact-sheet.jpg"
```

Assert topic 999 is rejected and topic 60 retains `60_git-worktree-cinematic.mp4`.

- [ ] **Step 2: Run tests and confirm topic-choice/path failures**

Run: `venv/bin/python -m unittest tests/test_render_cinematic.py -v`

Expected: FAIL because CLI choices and paths are hard-coded to 60.

- [ ] **Step 3: Add `ArtifactPaths` and topic-specific cache validation**

```python
@dataclass(frozen=True)
class ArtifactPaths:
    voice: Path
    metadata: Path
    video: Path
    preview: Path
    contact_sheet: Path

def voice_cache_matches(meta: dict, board: CinematicStoryboard) -> bool:
    return meta.get("topic_id") == board.topic_id and meta.get("voiceover") == board.voiceover
```

- [ ] **Step 4: Generalize rendering functions**

Replace topic-60 globals with parameters. `build_cinematic_clip(topic_id=60, ...)` selects the board through the registry, renders all narration shots, and switches to `render_frog_cta` only for the final natural-duration segment. Keep compatibility wrappers only where existing tests require them.

- [ ] **Step 5: Add a fast smoke-render test**

Render topic 61 at 216×384, 6 FPS, synthetic timings, and 1.0-second preview. Assert the resulting clip has the requested size/FPS and returns changing frames without calling network TTS.

- [ ] **Step 6: Run cinematic and export tests**

Run: `venv/bin/python -m unittest tests/test_render_cinematic.py tests/test_render_export_settings.py tests/test_cinematic_frog.py -v`

Expected: PASS.

- [ ] **Step 7: Package A checkpoint**

Run all cinematic tests:

`venv/bin/python -m unittest tests/test_cinematic_storyboard.py tests/test_cinematic_topics.py tests/test_cinematic_subtitles.py tests/test_cinematic_camera.py tests/test_cinematic_scene_registry.py tests/test_cinematic_scenes.py tests/test_cinematic_scene_families.py tests/test_cinematic_frog.py tests/test_render_cinematic.py tests/test_render_export_settings.py -v`

Expected: PASS. Report the exact count. If Git is available, commit with message `feat: generalize cinematic renderer for topic batches`.

---

## Package B — Scripts and storyboards 61–65

### Task 5: Verify claims and finalize five voiceovers

**Files:**
- Create: `docs/research/cinematic-topics-61-65-sources.md`
- Modify: `topics.json`
- Create: `tests/test_cinematic_topic_scripts.py`

**Interfaces:**
- Consumes: topic records 61–65.
- Produces: approved `voiceover`, `hook_text`, exact code excerpt, and source record for each topic.

- [ ] **Step 1: Create script quality tests before editing copy**

Test that each topic has: a hook under 90 characters; a voiceover between 75 and 115 whitespace tokens; exactly one limitation marker from (`но`, `важно`, `помни`); no unsupported absolute performance promises; and every code identifier displayed in the storyboard occurs verbatim in `topic["code"]` or `topic["voiceover"]`.

- [ ] **Step 2: Run tests and capture which current scripts violate the contract**

Run: `venv/bin/python -m unittest tests/test_cinematic_topic_scripts.py -v`

Expected: FAIL until all five scripts meet the contract.

- [ ] **Step 3: Verify each topic against primary official sources**

Browse only first-party documentation or standards material. Record page title, direct URL, access date, and the exact claim it supports. Verify especially version/status claims for React `use`, Node UUIDv7, Navigation API Baseline, TypeScript 6 defaults, and CSS `@starting-style`. If a claim is not supported, rewrite or remove it before storyboard work.

- [ ] **Step 4: Rewrite the five hooks and voiceovers**

Use this mandatory copy order in every script: concrete pain → cause → new mechanism → visible result → one limitation. Keep narration natural in Russian, remove catalog-like feature lists, and make each sentence map to one visual action.

- [ ] **Step 5: Run script tests**

Run: `venv/bin/python -m unittest tests/test_cinematic_topic_scripts.py -v`

Expected: PASS for IDs 61–65.

- [ ] **Step 6: Control Point 1 — user reviews scripts**

Present the five finalized voiceovers and concise scene outlines. Stop execution until the user explicitly approves or requests changes. Do not generate TTS or final MP4 files at this point.

- [ ] **Step 7: Checkpoint after approval**

Use the Git-or-report procedure with commit message `content: approve cinematic scripts for topics 61 to 65`.

### Task 6: Implement declarative storyboards 61–65

**Files:**
- Modify: `core/cinematic_topics.py`
- Create: `core/cinematic_topic_61.py`
- Create: `core/cinematic_topic_62.py`
- Create: `core/cinematic_topic_63.py`
- Create: `core/cinematic_topic_64.py`
- Create: `core/cinematic_topic_65.py`
- Modify: `tests/test_cinematic_topics.py`

**Interfaces:**
- Consumes: approved topic copy and registered scene kinds.
- Produces: `build_storyboard() -> CinematicStoryboard` in each topic module.

- [ ] **Step 1: Write failing semantic storyboard tests**

For every board, assert it contains semantic roles `problem`, `cause`, `mechanism`, `result`, and `limitation` in shot `scene_data["role"]`; no shot has `frog_reaction`; narration sentence ranges cover every sentence exactly once; and at least three different scene kinds are used.

- [ ] **Step 2: Run tests and confirm missing-builder failures**

Run: `venv/bin/python -m unittest tests/test_cinematic_topics.py -v`

Expected: FAIL because topic modules 61–65 do not exist.

- [ ] **Step 3: Build topic 61 and 62 storyboards**

Topic 61 uses `problem_ui → process_chain → code_build → data_flow → before_after → warning → resolution`. Topic 62 uses `index_tree(v4) → timeline → code_build → index_tree(v7) → before_after → warning → resolution`.

- [ ] **Step 4: Build topic 63–65 storyboards**

Topic 63 uses browser navigation and abort flow. Topic 64 uses configuration diff and diagnostic resolution. Topic 65 uses CSS state transition, code build, reduced-motion branch, and final comparison.

- [ ] **Step 5: Run registry, semantic, and retiming tests**

Run: `venv/bin/python -m unittest tests/test_cinematic_storyboard.py tests/test_cinematic_topics.py tests/test_cinematic_topic_scripts.py -v`

Expected: PASS.

- [ ] **Step 6: Checkpoint**

Use the Git-or-report procedure with commit message `feat: add cinematic storyboards for topics 61 to 65`.

---

## Package C — Preview review

### Task 7: Generate and visually verify contact sheets and silent previews

**Files:**
- Modify only if defects are found: cinematic modules from Packages A–B
- Generate: `output/{61..65}_*-cinematic-contact-sheet.jpg`
- Generate: `output/{61..65}_*-cinematic-preview.mp4`
- Create: `tests/test_cinematic_preview_artifacts.py`

**Interfaces:**
- Consumes: generalized CLI and storyboards 61–65.
- Produces: five contact sheets and five low-cost silent preview MP4 files.

- [ ] **Step 1: Add artifact validation tests**

Use `ffprobe` through `subprocess.run` and assert each generated preview has a video stream, vertical dimensions, 30 FPS, duration greater than zero, and no required audio stream. Use Pillow to assert each contact sheet opens and has non-zero dimensions.

- [ ] **Step 2: Render all contact sheets without network**

Run once per topic:

`venv/bin/python render_cinematic.py --topic 61 --skip-voice --contact-sheet --preview-duration 12`

Repeat with IDs 62, 63, 64, and 65. Rendering uses synthetic timings and must not invoke Edge TTS.

- [ ] **Step 3: Run artifact tests**

Run: `venv/bin/python -m unittest tests/test_cinematic_preview_artifacts.py -v`

Expected: PASS for all ten artifacts.

- [ ] **Step 4: Perform visual QA**

Inspect every contact sheet plus early/middle/late frames from each preview. Verify mobile readability, no overlapping subtitles/code, obvious temporal change, distinct visual metaphor per topic, and no frog before the outro. Fix concrete defects and repeat the relevant focused tests and preview only.

- [ ] **Step 5: Control Point 2 — user reviews previews**

Show clickable paths for all contact sheets and preview MP4 files. Stop until the user approves the visual direction or requests revisions.

- [ ] **Step 6: Package C checkpoint after approval**

Run the full cinematic suite from Task 4 and report the exact test count plus preview artifact paths. Commit code/test corrections if Git becomes available; generated output files stay uncommitted.

---

## Package D — Final audio and videos

### Task 8: Generate TTS, mix audio, render, and validate five final MP4s

**Files:**
- Generate: `temp/{61..65}_cinematic_voice.mp3`
- Generate: `temp/{61..65}_cinematic_voice.json`
- Generate: `output/{61..65}_*-cinematic.mp4`
- Create: `tests/test_cinematic_final_artifacts.py`

**Interfaces:**
- Consumes: user-approved scripts and previews.
- Produces: five publishable MP4 files and reusable voice timing metadata.

- [ ] **Step 1: Add final artifact checks before rendering**

For every final file, parse `ffprobe -show_streams -show_format -of json` and assert: 1080×1920; 30/1 FPS; H.264 video; AAC audio; `yuv420p`; duration equals narrated audio plus natural frog duration within 0.25 seconds; and total duration remains within the approved range implied by the natural outro.

- [ ] **Step 2: Generate or refresh TTS caches**

Run `venv/bin/python render_cinematic.py --topic 61 --contact-sheet`, then repeat for 62–65. Network approval may be required for Edge TTS. Cache metadata must include `topic_id`, exact `voiceover`, sentence timings, and word timings.

- [ ] **Step 3: Confirm optional audio degradation is honest**

If `assets/click.mp3` remains empty, keep the existing warning and render without it. Do not synthesize or silently substitute a fake effect. Confirm narration stays above background music and the frog outro retains its original playback speed.

- [ ] **Step 4: Run final artifact validation**

Run: `venv/bin/python -m unittest tests/test_cinematic_final_artifacts.py tests/test_render_export_settings.py -v`

Expected: PASS for all five files.

- [ ] **Step 5: Perform final visual/audio QA**

Watch each completed video from start to finish. Check that speech matches the displayed mechanism, captions highlight the active phrase, transitions do not hide code, no inline frog appears, and the full frog outro plays once without overlays or speed change.

- [ ] **Step 6: Control Point 3 — delivery**

Provide clickable paths, exact durations, codec verification, and the final test count for all five videos. List any skipped optional SFX warning. Do not claim upload or analytics work; both remain outside this package.

- [ ] **Step 7: Final checkpoint**

Run the complete targeted cinematic suite plus `venv/bin/python -m unittest tests/test_motion_storyboard.py tests/test_motion_closure.py -v` to protect the older motion path. If Git is available, commit source/tests with message `feat: complete cinematic batch 61 to 65`; otherwise provide a complete changed-file list.
