import re
import logging
from datetime import datetime, timedelta
from rapidfuzz import process
from rapidfuzz import fuzz

from database.db import get_connection

logger = logging.getLogger(__name__)


class AIProcessingError(Exception):
    """Custom exception for AI processing errors"""
    pass


# -------------------
# Intent Detection
# -------------------
def detect_intent(text):

    # Strong keyword-based rules first so that
    # "cancel" and "reschedule" are never misclassified as "book"
    lowered = text.lower()

    if any(word in lowered for word in ["cancel", "remove", "delete"]):
        return "cancel"

    if any(phrase in lowered for phrase in ["reschedule", "change time", "change appointment", "move appointment", "shift appointment"]):
        return "reschedule"

    intents = {
        "book": [
            "book appointment",
            "schedule appointment",
            "make appointment",
            "see doctor",
            "visit doctor",
            "meet doctor"
        ],
        "cancel": [
            "cancel appointment",
            "remove appointment",
            "delete appointment"
        ],
        "reschedule": [
            "reschedule appointment",
            "change appointment time",
            "move appointment",
            "shift appointment"
        ],
        "check_availability": [
            "available slots",
            "doctor availability",
            "free time"
        ]
    }

    best_match = None
    best_score = 0

    for intent, phrases in intents.items():

        match = process.extractOne(text, phrases)

        if match and match[1] > best_score:
            best_match = intent
            best_score = match[1]

    if best_score > 60:
        return best_match

    return None


# -------------------
# Doctor Cache
# -------------------
DOCTOR_CACHE = None


# -------------------
# Normalize Doctor Name
# -------------------
def normalize_doctor_name(name):

    name = name.lower()

    name = name.replace("doctor", "dr")
    name = name.replace("dr.", "dr")

    return name.strip()


# -------------------
# Doctor Matching
# -------------------
def match_doctor_from_db(text):

    global DOCTOR_CACHE

    try:

        if DOCTOR_CACHE is None:

            conn = get_connection()
            cur = conn.cursor()

            cur.execute("SELECT DISTINCT doctor_name FROM doctor_schedule")

            DOCTOR_CACHE = [normalize_doctor_name(row[0]) for row in cur.fetchall()]

            cur.close()
            conn.close()

        text = normalize_doctor_name(text)

        words = text.split()

        best_match = None
        best_score = 0

        for doctor in DOCTOR_CACHE:

            score = fuzz.partial_ratio(text, doctor)

            if score > best_score:

                best_score = score
                best_match = doctor

        if best_score > 70:
            return best_match

        return None

    except Exception as e:
        logger.error(f"Doctor matching error: {e}")
        return None
# -------------------
# Fuzzy Word Match
# -------------------
def fuzzy_word_match(text, target, threshold=80):

    words = text.split()

    for word in words:
        if fuzz.ratio(word, target) >= threshold:
            return True

    return False


# -------------------
# Convert Spoken Numbers (nine -> 9)
# -------------------
def convert_spoken_numbers(text):

    numbers = {
        "one": "1",
        "two": "2",
        "three": "3",
        "four": "4",
        "five": "5",
        "six": "6",
        "seven": "7",
        "eight": "8",
        "nine": "9",
        "ten": "10",
        "eleven": "11",
        "twelve": "12"
    }

    words = text.split()

    for i, word in enumerate(words):

        if word in numbers:

            if i + 1 < len(words) and words[i + 1] in ["am", "pm"]:

                words[i] = numbers[word]

    return " ".join(words)


# -------------------
# Main Processing
# -------------------
def process_user_command(text: str):

    try:

        if not text or not isinstance(text, str):
            raise ValueError("Invalid user input")

        text = text.lower().strip()

        # Normalize doctor words
        text = text.replace("doctor ", "dr ")
        text = text.replace("dr.", "dr ")
        text = text.replace("dr  ", "dr ")

        # Normalize time format
        text = text.replace("p.m.", "pm")
        text = text.replace("a.m.", "am")
        text = text.replace("p.m", "pm")
        text = text.replace("a.m", "am")

        # Convert spoken numbers
        text = convert_spoken_numbers(text)

        result = {
            "intent": None,
            "doctor": None,
            "date": None,
            "time": None,
            "old_time": None,
            "new_time": None
        }

        # -------------------
        # Intent Detection
        # -------------------
        intent = detect_intent(text)

        if intent:
            result["intent"] = intent
        else:
            raise AIProcessingError("Intent not detected")

        # -------------------
        # Doctor Detection
        # -------------------
        doctor = match_doctor_from_db(text)

        if doctor:
            result["doctor"] = doctor

        # -------------------
        # Time Detection
        # -------------------
        times = re.findall(r"\b\d{1,2}(?::\d{2})?\s*(?:am|pm)\b", text, re.IGNORECASE)

        if result["intent"] == "reschedule" and len(times) >= 2:
            result["old_time"] = times[0]
            result["new_time"] = times[1]
        elif result["intent"] == "reschedule" and len(times) == 1:
            # "move to 4 pm" - only new time; old_time will be looked up from existing appointment
            result["new_time"] = times[0]
        elif len(times) >= 1:
            result["time"] = times[0]

        # -------------------
        # Date Detection
        # -------------------
        date_match = re.search(r"\d{4}-\d{2}-\d{2}", text)

        if date_match:

            result["date"] = date_match.group()

        elif "day after tomorrow" in text:

            result["date"] = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

        elif fuzzy_word_match(text, "tomorrow"):

            result["date"] = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        elif fuzzy_word_match(text, "today"):

            result["date"] = datetime.now().strftime("%Y-%m-%d")

        return result


    except ValueError as e:

        logger.error(f"Input validation error: {e}")
        return {"error": "Invalid input"}

    except AIProcessingError as e:

        logger.error(f"AI processing error: {e}")
        return {"error": str(e)}

    except Exception as e:

        logger.error(f"Unexpected error: {e}")
        return {"error": "Internal AI processing error"}