from gtts import gTTS
import os
import uuid


def generate_speech(text: str, lang: str = "en"):
    """
    Generate an MP3 file from text.
    Lang defaults to English but can be "hi" or "ta" etc.
    """
    try:
        # create unique file name
        filename = f"audio_{uuid.uuid4()}.mp3"

        # fallback to English for unsupported language codes
        supported_langs = {"en", "hi", "ta"}
        tts_lang = lang if lang in supported_langs else "en"

        # generate speech
        tts = gTTS(text=text, lang=tts_lang)
        tts.save(filename)

        return filename

    except Exception as e:
        raise Exception(f"TTS Error: {str(e)}")