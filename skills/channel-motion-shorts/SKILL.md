---
name: channel-motion-shorts
description: Create Russian educational motion-design videos for the user's YouTube Shorts and Instagram Reels channel, especially requests for another topic in the approved React-video style, with Dmitry narration, music and the supplied frog subscription outro.
---

# Channel motion shorts

Use the approved channel defaults below unless the user changes them. This is a personal production recipe, not a rule for unrelated videos. Read the installed HyperFrames entry skill, then use general-video/faceless-explainer for the complete film and motion-graphics techniques for individual beats. Those skills are already installed; do not reinstall the entire pack on every run. Load their relevant composition, animation, CLI, media and audio guidance when needed.

## Approved defaults

- Deliver an actual MP4 for YouTube Shorts and Instagram Reels: 1080×1920, 9:16, 30 fps, normally 45–60 seconds **including** the outro.
- Russian educational content; clean, premium, energetic technical motion design. Dark #080D16, white #F4F7FC, blue #409CFF, lime #C5F86B and orange #FF9562. Montserrat display/body and JetBrains Mono labels, embedded locally.
- Large short kinetic phrases, diagrams and progressive visual explanations; purposeful slide/zoom/depth motion. Keep the story understandable with sound off. No talking heads or realistic people unless requested.
- Arc: hook in first 3s → simple explanation → mechanism → practical example → one takeaway → subscribe.
- **Always include narration and background music by default for this channel.** Existing project uses Edge TTS `ru-RU-DmitryNeural`; absence of HeyGen authentication is not evidence that voice generation is unavailable. Inspect the project before declaring a missing provider.
- Finish with the user's supplied frog.mp4, approximately 4.04s, and Russian spoken CTA: «Подпишись, чтобы не пропустить новые разборы». The file itself has no audio. Keep its existing red illustration and SUBSCRIBE text; it is an approved exception to the main dark visual style.
- Lower music under speech with HyperFrames Audio Carve, including spectral space for voice, and retain audible music through the outro. Avoid clipping and abrupt endings.

## Start a new topic

1. Read [production.md](references/production.md) for installed tools, resource paths, working audio and export commands. Prefer existing working infrastructure.
2. Create a separate `videos/<topic-slug>/` project. Never overwrite the approved example or another topic. The bundled `assets/approved-example/` is a **reference**, not a ready script for a new subject. It includes topic-specific Russian text and timing.
3. Research current/technical claims using authoritative sources. Select a suitable angle for the requested topic; do not assume every video is about a vulnerability. Date historical events and avoid stale version recommendations. Save sources beside the new project.
4. Write fresh BRIEF.md, frame.md, STORYBOARD.md and narration.json. Choose timing including the frog slot. Borrow visual grammar, typography and technical contracts from the reference; redesign diagrams to explain the new topic. Remove all old React/RSC/security wording unless relevant.
5. Generate narration early and measure it. Align each spoken segment to its corresponding visual scene, with short pauses. If it needs more than about 1.18× acceleration, shorten the wording or reallocate scene time rather than making speech rushed. Keep the total within the requested duration.
6. Build seek-safe HyperFrames scenes, assemble full-duration music plus narration, append frog and hide main-film headers/footers during it. Run the audio carve after final narration timing. Preserve the user's new decisions over these defaults.
7. Run HyperFrames check, inspect one contact sheet covering all scenes and the outro, then render within the user's authorized scope. Verify MP4 dimensions, actual duration, audio stream and peak level; inspect final-output frames. Deliver a clickable absolute MP4 path, actual duration and a short note that narration, music and subscription outro are included. Do not publish to social accounts unless separately authorized.

## Reuse safely

No narration from a previous subject may survive into a new deliverable. Cache voice by text, voice and rate (or generate into a fresh topic folder). Font and JS files may be reused; old audio caches, baked audio-carve attributes and source citations must be replaced. Run synthesis scripts from the new project directory; some use relative `public/` paths. Adapt the reference's hardcoded narration/timing before executing it.

Invocation example: «Используй $channel-motion-shorts. Создай ролик про Docker: зачем нужны контейнеры».
