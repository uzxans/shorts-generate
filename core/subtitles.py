import whisper

_model = None


def _get_model():
    global _model
    if _model is None:
        _model = whisper.load_model("base")
    return _model


def generate_word_timestamps(audio_path):
    result = _get_model().transcribe(audio_path, word_timestamps=True)

    words = []
    for seg in result["segments"]:
        for w in seg["words"]:
            words.append({
                "word": w["word"],
                "start": w["start"],
                "end": w["end"]
            })
    return words
