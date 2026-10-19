# Motion Explainer V2 Design

## Goal

Create a separate video format that matches the provided reference style: calm product-motion explainer, one visual idea per scene, male Yandex SpeechKit voice, slower pacing, and no rapid switching between code/demo/keypoint windows.

## Reference Breakdown

The reference video in `input/SaveClip.App_AQNKsp8_j4xP-gSBSxLTrQFwFeRXKLqxnVlHWFNhKJOrpn2d99OqR9x9cyFkTK3X6vSr359WlHoKF9-O8bvS800kBr-Po8AQcMkWAKs.mp4` uses:

- Vertical `720x1280`, `30fps`, about `54.5s`.
- Dark grid background with subtle low-contrast texture.
- One central UI object that evolves smoothly instead of scene cuts.
- Short headline phrases with one highlighted accent phrase.
- Tiny labels and code notes as supporting detail, not the main content.
- Calm pacing with clear visual states and breathing room.

## First Target Video

Use topic `36` from `topics.json`, but rewrite it as a motion explainer about closures:

- Core idea: "Замыкание — это память функции."
- Visual metaphor: two counters created from the same factory function keep independent values.
- Output duration target: `50-60s`.
- Render target: `1080x1920`, `30fps`.

## Storyboard

1. `0-4s`: show one sentence, "Замыкание — это память функции."
2. `4-12s`: reveal `makeCounter(0)` as the first counter card.
3. `12-22s`: reveal `makeCounter(100)` as the second counter card.
4. `22-34s`: show a small code-note: `let count` stays inside.
5. `34-46s`: animate button taps and independent number changes.
6. `46-55s`: final statement, "Каждый вызов создает свою память."

## Visual Direction

- Background: near-black grid, subtle vignette, very low motion.
- Typography: large bold white text, accent words in cyan/teal.
- UI: rounded dark cards, cyan focus glow, restrained shadows.
- Motion: fades, slides, scale pulses, glow changes, no hard cuts unless necessary.
- Code: small bottom notes only; avoid full code panels in this format.

## Voice Direction

Use Yandex SpeechKit instead of Edge TTS for this renderer.

- Preferred voice: `ermil`.
- Fallback voices: `kirill`, `anton`, `zahar`.
- Speed: `0.85-0.9`.
- Use SSML pauses between scene sentences.
- Store credentials in environment variables, not in source:
  - `YANDEX_API_KEY`
  - optional `YANDEX_FOLDER_ID`
  - optional `YANDEX_TTS_VOICE`

## Architecture

Add this as a separate v2 path, not a rewrite of the existing renderer:

- New script: `render_motion.py`.
- New module: `core/yandex_tts.py`.
- New module: `core/motion_closure.py` for the first motion scene.
- Keep current `render.py` intact for the existing Shorts format.

## Testing

- Unit-test Yandex request building without making network calls.
- Unit-test storyboard timing totals.
- Smoke-test one rendered sample locally after credentials are configured.

## Acceptance Criteria

- Generates one full topic `36` v2 video without using the old code/demo/keypoints layout.
- Uses male Yandex SpeechKit voice when credentials are present.
- Falls back with a clear error if credentials are missing.
- Keeps scene transitions calm and avoids rapid window switching.
- Final video uses the existing high-quality export profile.
