# Working environment and production details

## Existing project and approved reference

Workspace: `/Users/tim/work/videoPro/shorts-generator`.
Approved project: `videos/react-server-components-critical/`.
Approved final: `renders/react-server-components-voice-subscribe.mp4` inside that project (58.033s, H.264 + AAC, 1080×1920, 30fps).
Bundled reference: `../assets/approved-example/` relative to this reference directory. It contains editable composition, local fonts/GSAP, frog, palette, script examples and screenshot. It deliberately excludes generated narration and music: regenerate for the new topic.
Original channel outro: workspace `assets/frog.mp4`; bundled fallback `assets/approved-example/public/frog.mp4` under the skill. Source is 464×832, 4.041667s, no audio; preserve aspect when filling portrait canvas. At 30fps the approved slot used 4.033333s.

## Narration already installed

Python: workspace `venv/bin/python`; package `edge_tts`.
Existing configuration: `render.py` sets `VOICE = "ru-RU-DmitryNeural"`. `render_cinematic.py` also uses it. `core/yandex_tts.py` is another configured integration but requires Yandex credentials; Edge TTS is the working default for this recipe.
Edge TTS needs network access, despite the package being installed locally. If access fails, report the actual error and try an available authorized alternative; do not silently omit narration.

Reference `narrate.py` generates each scene with `edge_tts.Communicate(text, 'ru-RU-DmitryNeural', rate='+5%')`. **Its text and slots are topic-specific; replace them.** Read and adapt `align_voice.py` alongside it. The narration JSON shape is an array of `[start_seconds, slot_seconds, russian_text]`. Make the start of each segment agree with the scene start.

Audio timing invariants:

- Measure generated files using ffprobe; nominal TTS speed does not guarantee duration.
- Pitch-preserving atempo can fit modest overrun. Prefer rewriting over excessive acceleration.
- Convert to the same 44100Hz mono signed 16-bit PCM format, normalize voice consistently, add a small lead-in.
- After conversion, pad/truncate **PCM samples** to exactly the scene slot (slot×44100 samples); ffmpeg filter durations alone produced short output in this environment. Concatenate exact slots or place tracks at explicit starts. Otherwise later voice drifts before its visuals.
- Place narration as a separate `<audio id="narration" ...>`; every audio requires an id. Music should have its own id, e.g. soundtrack. Source duration must cover authored slots.
- Reference `make_soundtrack.py` is original deterministic electronic synthesis, not copyrighted sampled music. Adapt duration and phrase ending to the new timeline; run from the new project root. Existing `assets/music.mp3` can instead be used when chosen by the user.

## Mix

Read hyperframes-audio before processing. Working command from new project root:

```sh
node /Users/tim/.agents/skills/hyperframes-audio/scripts/carve.mjs --comp index.html --bed soundtrack --voice narration
```

Requires project-local `@hyperframes/core` (the tested version is 0.8.36). If genuinely absent, install a compatible version; the CLI's bundled internals alone did not satisfy carve.mjs. Re-run carve after changing speech or timing; it writes FX and volume envelopes to the bed in index.html. Do not copy baked envelopes from the old subject. Keep original source music and voice for further revisions.

## HyperFrames contracts and checks

Tested CLI: 0.8.36. Follow installed CLI upgrade checks when resuming later; do not silently assume this version is latest. The reference's scripts pin it for reproducibility.
Each scene: matching host/internal/timeline id, sized root, style and script **inside** template, paused GSAP timeline. Local asset URLs are project-relative `public/...`, never `../../public/...`. Use explicit start/duration on video and avoid a timed plain ancestor of a timed video.
Frog is a full-screen timed video with muted/playsinline, separate voiced CTA. Hide persistent main headers at the outro start (`tl.set('.chrome,.timeline',{autoAlpha:0},outroStart)`).

```sh
npx hyperframes check --at <scene-proof-times-and-outro>
npx hyperframes snapshot --at <scene-proof-times-and-outro>
npx hyperframes render --quality high --fps 30 --workers 2 --output renders/video.mp4
```

Inspect snapshots and verify actual output; a passing metadata check cannot prove mounted scenes or embedded video look correct. Original video checks had transient information-only container/connector notices; assess each new finding from pixels rather than suppressing the category.

If temporary disk preflight refuses capture, the tested streaming fallback preserves resolution:

```sh
PRODUCER_STREAMING_ENCODE_MAX_DURATION_SECONDS=120 npx hyperframes render --quality high --fps 30 --workers 1 --low-memory-mode --output renders/video.mp4
```

`--low-memory-mode` alone did not enable streaming for the 58-second film; the duration environment setting was also required. Do not delete unrelated user files to make space.

Verify with ffprobe (duration, size, audio/video codecs, 1080×1920, 30fps), sample final MP4 frames, and check final audio peak below 0dBFS. The approved mix measured mean -17.1dBFS and max -1.1dBFS; these are observations, not universal loudness targets. Keep music discernible and speech clear.
