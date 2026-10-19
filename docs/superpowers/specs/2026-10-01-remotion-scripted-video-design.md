# Remotion-driven scripted shorts

## Goal

Generate a topic-specific vertical short where the script, on-screen text,
visual motion, narration, and captions are all driven by the same validated
scene data. Replace the current generic HyperFrames scene artwork for scripted
topics; keep the existing `shorts <topic-id>` entry point and Russian narration.

## User-visible behavior

- `shorts 57` renders a 1080×1920, 30fps video from `topics.json`.
- Each scene uses its own topic data instead of generic placeholder cards.
- Scene text and narration refer to the same concept and scene interval.
- Word-level captions follow the generated narration.
- The final outro is optional and remains a separate, explicitly timed segment.
- Existing `--skip-voice`, `--build-only`, `--validate-script`, and
  `--max-duration` behavior remains available where meaningful.

## Architecture

Remotion becomes the renderer for `script_timeline` topics. The existing Python
timeline validator and TTS preparation remain the source of truth for scene
intervals and narration metadata. A small JSON asset is written into the
Remotion project containing the validated board and caption cues.

The Remotion composition has one component per scene family:

- `TitleScene`: topic title, hook, and a visual metaphor derived from the
  scene's screen text.
- `CodeScene`: syntax-colored code, line reveals, and highlighted lines from
  the scene's `code` and `highlights` fields.
- `LayerScene`: stacked/ordered cards for cascade, priority, or sequence
  concepts, with labels derived from the script.
- `GradientScene`: animated CSS-style diagram driven by the scene's text and
  numeric animation settings.
- `TakeawayScene`: animated checklist based on `points`.
- `GenericScene`: a constrained fallback for supported scene types without a
  dedicated semantic renderer; it must still render scene-specific text.

The renderer uses React/SVG/CSS primitives for deterministic, crisp visuals.
It does not require an external image-generation API for the first version.
Topic-specific raster/video assets can be added later without changing the
scene contract.

## Media and verification

Use Remotion media primitives for audio and the installed multimedia tooling
for metadata checks. Mediabunny is used where browser-side media duration or
dimensions are needed; existing `ffprobe` checks remain acceptable for the
Python preparation boundary.

Before export, validate:

1. Every scene is contiguous and within the requested duration.
2. Every narration segment has a matching scene index and interval.
3. Caption cues fall inside their scene interval.
4. The rendered media duration matches the board duration within tolerance.
5. The selected topic's scene text is present in the generated composition
   data; no stale project or generic topic data may be used.

## Dependencies

Add Remotion packages required by the composition, CLI rendering, and caption
utilities, plus Mediabunny for media inspection. Keep HyperFrames dependencies
until the migration is verified, then remove only the scripted-render path's
unused dependency if all existing tests and commands remain green.

## Compatibility and migration

The legacy non-scripted renderer and cinematic renderer are out of scope. The
new path is selected only when a topic has `script_timeline`. Output filenames
remain under `output/` with the existing topic-based naming convention.

## Testing

- Unit-test the scene router and each semantic scene's data mapping.
- Test caption and audio interval validation with malformed boards.
- Render topic 57 in silent and narrated modes.
- Run the existing Python and JavaScript test suites.
- Inspect a rendered frame from each scene boundary and verify the audio file
  duration against the board.
