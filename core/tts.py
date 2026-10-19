import os

from elevenlabs.client import ElevenLabs

# Adam — deep male voice; works well with eleven_multilingual_v2 for RU+EN code-switching.
# Override with TTS_VOICE_ID env var to try another voice.
DEFAULT_VOICE_ID = "pNInz6obpgDQGcFmaJgB"
MODEL_ID = "eleven_multilingual_v2"
OUTPUT_FORMAT = "mp3_44100_128"

VOICE_SETTINGS = {
    "stability": 0.4,
    "similarity_boost": 0.75,
    "style": 0.6,
    "use_speaker_boost": True,
}

DEFAULT_API_KEY = "sk_da925b8f79a3e8cef46584202d9fb6ffaa88ddc931136c73"


def generate_voice(text, path):
    api_key = os.environ.get("ELEVENLABS_API_KEY", DEFAULT_API_KEY)
    if not api_key:
        raise RuntimeError("ELEVENLABS_API_KEY is not set")

    voice_id = os.environ.get("TTS_VOICE_ID", DEFAULT_VOICE_ID)

    client = ElevenLabs(api_key=api_key)
    audio_iter = client.text_to_speech.convert(
        voice_id=voice_id,
        model_id=MODEL_ID,
        output_format=OUTPUT_FORMAT,
        text=text,
        voice_settings=VOICE_SETTINGS,
    )

    tmp_path = path + ".part"
    written = 0
    try:
        with open(tmp_path, "wb") as f:
            for chunk in audio_iter:
                if chunk:
                    f.write(chunk)
                    written += len(chunk)
        if written < 1024:
            raise RuntimeError(f"ElevenLabs returned only {written} bytes — likely API error")
        os.replace(tmp_path, path)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
