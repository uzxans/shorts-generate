from __future__ import annotations

import os
from pathlib import Path


YANDEX_TTS_URL = "https://tts.api.cloud.yandex.net/speech/v1/tts:synthesize"


def build_yandex_tts_request(
    text: str,
    *,
    voice: str = "ermil",
    speed: str = "0.88",
    emotion: str = "neutral",
    folder_id: str | None = None,
) -> tuple[str, dict[str, str], dict[str, str]]:
    api_key = os.environ.get("YANDEX_API_KEY", "test-key")
    data = {
        "text": text,
        "lang": "ru-RU",
        "voice": voice,
        "emotion": emotion,
        "speed": speed,
        "format": "mp3",
    }
    if folder_id:
        data["folderId"] = folder_id
    return YANDEX_TTS_URL, {"Authorization": f"Api-Key {api_key}"}, data


def synthesize_yandex_tts(
    text: str,
    out_path: Path,
    *,
    api_key: str | None = None,
    folder_id: str | None = None,
    voice: str | None = None,
    speed: str = "0.88",
) -> Path:
    key = api_key or os.environ.get("YANDEX_API_KEY")
    if not key:
        raise RuntimeError("YANDEX_API_KEY is required for Yandex SpeechKit TTS")

    old_key = os.environ.get("YANDEX_API_KEY")
    os.environ["YANDEX_API_KEY"] = key
    try:
        url, headers, data = build_yandex_tts_request(
            text,
            voice=voice or os.environ.get("YANDEX_TTS_VOICE", "ermil"),
            speed=speed,
            folder_id=folder_id or os.environ.get("YANDEX_FOLDER_ID"),
        )
    finally:
        if old_key is None:
            os.environ.pop("YANDEX_API_KEY", None)
        else:
            os.environ["YANDEX_API_KEY"] = old_key

    import requests

    response = requests.post(url, headers=headers, data=data, timeout=120)
    response.raise_for_status()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(response.content)
    return out_path
