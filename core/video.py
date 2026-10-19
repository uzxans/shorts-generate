import os

from moviepy import (
    AudioFileClip,
    concatenate_videoclips,
)

from core.demo import render_demo_video
from core.effects import hook_scene, code_typing_scene, demo_scene, subscribe_scene, W, H

HOOK_DUR = 3.0
TYPING_DUR = 8.0
DEMO_DUR = 5.0
SUBSCRIBE_DUR = 3.0
TOTAL_DUR = HOOK_DUR + TYPING_DUR + DEMO_DUR + SUBSCRIBE_DUR

MUSIC_PATH = "assets/music.mp3"
MUSIC_VOLUME = 0.35


def build_video(topic, output_path):
    demo_recording_dur = max(HOOK_DUR, DEMO_DUR) + 1.0
    demo_path = render_demo_video(topic["demo_html"], duration=demo_recording_dur, w=W, h=H)

    s1 = hook_scene(topic["hook_text"], demo_path, HOOK_DUR)
    s2 = code_typing_scene(topic["code"], topic.get("language", "css"), TYPING_DUR)
    s3 = demo_scene(demo_path, DEMO_DUR)
    s4 = subscribe_scene(SUBSCRIBE_DUR)

    final = concatenate_videoclips([s1, s2, s3, s4], method="compose")

    if os.path.exists(MUSIC_PATH):
        music = AudioFileClip(MUSIC_PATH)
        if music.duration > final.duration:
            music = music.subclipped(0, final.duration)
        music = music.with_volume_scaled(MUSIC_VOLUME)
        final = final.with_audio(music)
    else:
        print(f"   ⚠️  фоновая музыка не найдена ({MUSIC_PATH}) — видео без звука")

    final.write_videofile(
        output_path,
        fps=30,
        codec="libx264",
        audio_codec="aac",
    )
