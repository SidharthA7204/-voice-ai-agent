import tempfile
import shutil
import os
import logging
import re

from faster_whisper import WhisperModel
from rapidfuzz import process
from word2number import w2n

logger = logging.getLogger(__name__)

# Load model once (FASTER)
model = WhisperModel(
    "base",
    device="cpu",
    compute_type="int8"
)


# -------------------------
# Normalize Text
# -------------------------
def normalize_text(text: str):

    text = text.lower().strip()

    text = text.replace("doctor", "dr")
    text = text.replace("dr.", "dr")

    text = re.sub(r"[^\w\s:]", "", text)

    return text


# -------------------------
# Fix pronunciation mistakes
# -------------------------
def correct_pronunciation(text: str):

    common_words = [
        "doctor",
        "appointment",
        "cancel",
        "reschedule",
        "tomorrow",
        "today"
    ]

    words = text.split()
    corrected = []

    for word in words:

        match = process.extractOne(word, common_words)

        if match and match[1] > 80:
            corrected.append(match[0])
        else:
            corrected.append(word)

    return " ".join(corrected)


# -------------------------
# Convert spoken numbers
# -------------------------
def convert_spoken_numbers(text):

    words = text.split()

    for i, word in enumerate(words):

        try:
            number = w2n.word_to_num(word)

            if 1 <= number <= 12:

                if i + 1 < len(words):

                    if words[i + 1] in ["am", "pm"]:
                        words[i] = str(number)

        except:
            pass

    return " ".join(words)


# -------------------------
# Transcribe Audio
# -------------------------
def transcribe_audio(audio_file):

    temp_path = None

    try:

        if not audio_file:
            raise ValueError("No audio file")

        # Save uploaded audio temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            shutil.copyfileobj(audio_file.file, temp_audio)
            temp_path = temp_audio.name

        logger.info("Audio saved: %s", temp_path)

        # Faster Whisper transcription
        segments, info = model.transcribe(
            temp_path,
            beam_size=1,
            language="en"
        )

        text = ""

        for segment in segments:
            text += segment.text

        if not text.strip():
            raise ValueError("No speech detected")

        logger.info("Raw text: %s", text)

        # Step 1 normalize
        text = normalize_text(text)

        # Step 2 pronunciation correction
        text = correct_pronunciation(text)

        # Step 3 convert spoken numbers
        text = convert_spoken_numbers(text)

        logger.info("Processed text: %s", text)

        return text

    except Exception as e:

        logger.error("Speech processing error: %s", str(e))
        return None

    finally:

        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)