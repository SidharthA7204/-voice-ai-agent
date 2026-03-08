from fastapi import FastAPI, HTTPException, UploadFile, File
from services.speech_to_text import transcribe_audio
from database.db import get_connection
from agent.intent_parser import process_user_command
from datetime import datetime
from services.text_to_speech import generate_speech
from fastapi.responses import FileResponse
from services.language_detector import detect_language
from memory.session_memory import store_session, get_session
from backend.routes.websocket import router as websocket_router
from typing import List, Any
import time
import logging
import re

app = FastAPI()
app.include_router(websocket_router)

latency_logger = logging.getLogger("latency")


def normalize_time_value(value: Any) -> str | None:
    """
    Convert different time representations (e.g. '4 pm', '4pm', '16:00', time object)
    into a unified 'HH:MM:SS' string so comparisons and DB writes are reliable.
    """
    if value is None:
        return None

    # Handle datetime.time or similar objects (from Postgres)
    if hasattr(value, "strftime"):
        try:
            return value.strftime("%H:%M:%S")
        except Exception:
            return None

    # Handle string inputs
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        lower = s.lower()

        # 12-hour formats: '4 pm', '4:30 pm', '4pm', '4:30pm'
        if "am" in lower or "pm" in lower:
            m = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", lower)
            if m:
                h, mi, ampm = int(m.group(1)), int(m.group(2) or 0), m.group(3)
                t_str = f"{h}:{mi:02d} {ampm}" if mi else f"{h} {ampm}"
                try:
                    dt = datetime.strptime(t_str, "%I:%M %p")
                except ValueError:
                    dt = datetime.strptime(t_str, "%I %p")
                return dt.strftime("%H:%M:%S")

        # 24-hour 'HH:MM' (5 chars)
        if len(s) == 5 and ":" in s:
            return f"{s}:00"

        # Already 'HH:MM:SS' or 'HH:MM'
        if ":" in s:
            parts = s.split(":")
            if len(parts) >= 2:
                try:
                    h, m = int(parts[0]), int(parts[1])
                    sec = int(parts[2]) if len(parts) > 2 else 0
                    return f"{h:02d}:{m:02d}:{sec:02d}"
                except (ValueError, IndexError):
                    pass
        return s

    return None


def _time_matches_slot(user_time: str | None, slot: str | None) -> bool:
    """Compare user time (e.g. '5pm', '17:00') with slot (e.g. '17:00:00') using HH:MM."""
    if not user_time or not slot:
        return False
    u = normalize_time_value(user_time)
    s = normalize_time_value(slot)
    if not u or not s:
        return False
    return u == s or (u[:5] == s[:5])


def _get_normalized_slots(raw_slots: Any) -> List[str]:
    """
    Extract and normalize slots from doctor_schedule.available_slots.
    Handles: list, array, comma-separated string, single value, None.
    Returns sorted list of 'HH:MM:SS' strings (unbooked logic is separate).
    """
    result: List[str] = []
    if raw_slots is None:
        return result

    items = raw_slots
    if isinstance(raw_slots, str):
        items = [x.strip() for x in raw_slots.replace(",", " ").split() if x.strip()]
    elif not isinstance(raw_slots, (list, tuple)):
        items = [raw_slots]

    for slot in items:
        n = normalize_time_value(slot)
        if n:
            result.append(n)
    return sorted(set(result))

# Get all doctors and schedules
@app.get("/doctors")
def get_doctors():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT doctor_name, date, available_slots FROM doctor_schedule")
        rows = cur.fetchall()

        doctors = []

        for row in rows:
            doctors.append({
                "doctor_name": row[0],
                "date": str(row[1]),
                "available_slots": row[2]
            })

        return doctors

    except Exception as e:
        return {"error": str(e)}

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


# Book Appointment
@app.post("/book-appointment")
def book_appointment(data: dict):

    try:
        doctor = data.get("doctor_name")
        date = data.get("date")
        time = data.get("time")
        patient = data.get("patient_name")

        if doctor:
            doctor = doctor.lower().strip()

        if time:
            # Normalize any user-provided time to 'HH:MM:SS'
            time = normalize_time_value(time)

        if date:
            try:
                date = datetime.strptime(date, "%Y-%m-%d").date()
            except:
                pass

        if not doctor or not date or not time or not patient:
            return {"message": "Missing required fields"}

        # Reject bookings in the past
        try:
            appointment_dt = datetime.combine(
                date,
                datetime.strptime(time, "%H:%M:%S").time()
            )
            if appointment_dt <= datetime.now():
                return {"message": "Cannot book an appointment in the past"}
        except Exception:
            # If parsing fails, fall through – DB constraints will still protect us
            pass

        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "SELECT doctor_name, date, available_slots FROM doctor_schedule WHERE LOWER(doctor_name)=LOWER(%s) AND date=%s",
            (doctor, date)
        )

        doctor_row = cur.fetchone()

        if not doctor_row:
            return {"message": "Doctor not available on this date"}

        # Normalize schedule slots; handle list, array, or string from DB
        schedule_slots = _get_normalized_slots(doctor_row[2])
        if not schedule_slots:
            return {"message": "Doctor has no slots on this date"}

        # Get booked slots for this doctor+date to build unbooked list
        cur.execute(
            """
            SELECT time FROM appointments
            WHERE LOWER(doctor_name)=LOWER(%s) AND date=%s AND status='booked'
            """,
            (doctor, date)
        )
        booked_times = {normalize_time_value(t[0]) for t in cur.fetchall() if t[0]}
        unbooked_slots = [s for s in schedule_slots if s not in booked_times]

        # Match: requested time (e.g. 5pm) must be in schedule slots (e.g. 17:00:00)
        in_schedule = any(_time_matches_slot(time, s) for s in schedule_slots)
        if not in_schedule:
            return {"message": "Selected slot not available"}

        cur.execute(
            """
            SELECT * FROM appointments
            WHERE LOWER(doctor_name)=LOWER(%s)
            AND date=%s
            AND time=%s
            AND status='booked'
            """,
            (doctor, date, time)
        )

        existing = cur.fetchone()

        if existing:
            return {
                "message": "Slot already booked",
                "alternatives": unbooked_slots[:3]
            }

        cur.execute(
            "INSERT INTO appointments (patient_name, doctor_name, date, time, status) VALUES (%s,%s,%s,%s,%s)",
            (patient, doctor, date, time, "booked")
        )

        conn.commit()

        return {
            "message": "Appointment booked successfully",
            "doctor": doctor,
            "time": time
        }

    except Exception as e:
        return {"error": str(e)}

    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()


# Cancel Appointment
@app.delete("/cancel-appointment")
def cancel_appointment(data: dict):

    doctor = data.get("doctor_name")
    date = data.get("date")
    time = data.get("time")
    patient = data.get("patient_name")

    if time:
        time = normalize_time_value(time)
    if date:
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except:
            pass

    if not doctor or not date or not time or not patient:
        raise HTTPException(
            status_code=400,
            detail="doctor_name, date, time, and patient_name are required"
        )

    conn = None
    cur = None

    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT * FROM appointments
            WHERE patient_name=%s AND LOWER(doctor_name)=LOWER(%s) AND date=%s AND time=%s
            """,
            (patient, doctor, date, time)
        )

        appointment = cur.fetchone()

        if not appointment:
            raise HTTPException(
                status_code=404,
                detail="Appointment not found"
            )

        cur.execute(
            """
            UPDATE appointments
            SET status='cancelled'
            WHERE patient_name=%s AND LOWER(doctor_name)=LOWER(%s) AND date=%s AND time=%s
            """,
            (patient, doctor, date, time)
        )

        conn.commit()

        return {
            "message": "Appointment cancelled successfully",
            "doctor": doctor,
            "time": time
        }

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# Reschedule Appointment
@app.put("/reschedule-appointment")
def reschedule_appointment(data: dict):

    patient = data.get("patient_name")
    doctor = data.get("doctor_name")
    old_time = data.get("old_time")
    new_time = data.get("new_time")
    date = data.get("date")

    if old_time:
        old_time = normalize_time_value(old_time)

    if new_time:
        new_time = normalize_time_value(new_time)

    if date:
        try:
            date = datetime.strptime(date, "%Y-%m-%d").date()
        except:
            pass

    conn = None
    cur = None

    if not patient or not doctor or not new_time or not date:
        raise HTTPException(
            status_code=400,
            detail="patient_name, doctor_name, new_time and date are required"
        )

    try:
        conn = get_connection()
        cur = conn.cursor()

        # If old_time not provided, look up existing booked appointment for this patient+doctor+date
        if not old_time:
            cur.execute(
                """
                SELECT time FROM appointments
                WHERE patient_name=%s AND LOWER(doctor_name)=LOWER(%s) AND date=%s AND status='booked'
                LIMIT 1
                """,
                (patient, doctor, date)
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="No existing appointment found to reschedule")
            old_time = normalize_time_value(row[0])

        cur.execute(
            """
            SELECT * FROM appointments
            WHERE patient_name=%s AND LOWER(doctor_name)=LOWER(%s) AND date=%s AND time=%s AND status='booked'
            """,
            (patient, doctor, date, old_time)
        )

        appointment = cur.fetchone()

        if not appointment:
            raise HTTPException(
                status_code=404,
                detail="Original appointment not found"
            )

        cur.execute(
            """
            SELECT available_slots FROM doctor_schedule
            WHERE LOWER(doctor_name)=LOWER(%s) AND date=%s
            """,
            (doctor, date)
        )

        schedule = cur.fetchone()
        schedule_slots = _get_normalized_slots(schedule[0] if schedule else None)
        if not schedule_slots:
            raise HTTPException(
                status_code=400,
                detail="Doctor has no slots on this date"
            )

        # Match new_time (e.g. 5pm) with schedule slots (e.g. 17:00:00)
        in_schedule = any(_time_matches_slot(new_time, s) for s in schedule_slots)
        if not in_schedule:
            raise HTTPException(status_code=400, detail="Selected slot not available")

        # New slot must not be taken by another patient (our old slot is OK - we're vacating it)
        new_hm = (new_time or "")[:5]
        cur.execute(
            """
            SELECT time FROM appointments
            WHERE LOWER(doctor_name)=LOWER(%s) AND date=%s AND status='booked'
            """,
            (doctor, date)
        )
        booked_times = {normalize_time_value(t[0]) for t in cur.fetchall() if t[0]}
        booked_times.discard(old_time)
        new_taken = new_time in booked_times or any((b or "")[:5] == new_hm for b in booked_times)
        if new_taken:
            raise HTTPException(status_code=400, detail="Selected slot not available")

        cur.execute(
            """
            UPDATE appointments
            SET time=%s
            WHERE patient_name=%s AND LOWER(doctor_name)=LOWER(%s) AND date=%s AND time=%s
            """,
            (new_time, patient, doctor, date, old_time)
        )

        conn.commit()

        return {
            "message": "Appointment rescheduled",
            "new_time": new_time
        }

    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


# AI Agent Endpoint
@app.post("/ai-agent")
def ai_agent(data: dict):

    message = data.get("message")

    if not message:
        return {"error": "Message required"}

    result = process_user_command(message)

    if not result:
        return {"error": "AI could not understand the request"}

    intent = result.get("intent")
    doctor = result.get("doctor")
    date = result.get("date")
    time = result.get("time")

    if intent == "book":
        return book_appointment({
            "doctor_name": doctor,
            "date": date,
            "time": time,
            "patient_name": "AI User"
        })

    elif intent == "cancel":
        return cancel_appointment({
            "doctor_name": doctor,
            "date": date,
            "time": time,
            "patient_name": "AI User"
        })

    elif intent == "reschedule":
        return reschedule_appointment({
            "doctor_name": doctor,
            "patient_name": "AI User",
            "date": date,
            "old_time": result.get("old_time"),
            "new_time": result.get("new_time")
        })


@app.post("/voice-agent")
async def voice_agent(audio: UploadFile = File(...)):

    try:
        t_start = time.time()

        # STEP B - Speech to Text
        text = transcribe_audio(audio)
        t_stt = time.time()

        if not text:
            return {"error": "Could not detect speech"}

        print("User said:", text)

        # STEP C - Detect Language
        try:
            language = detect_language(text)
        except Exception:
            language = "en"
        t_lang = time.time()

        # STEP D - AI Agent (intent + slots)
        result = process_user_command(text)
        t_agent = time.time()

        if not result or result.get("error"):
            response_text = "Sorry, I could not understand your request."
            audio_file = generate_speech(response_text, lang=language)
            return FileResponse(audio_file, media_type="audio/mpeg", filename="response.mp3")

        intent = result.get("intent")
        doctor = result.get("doctor")
        date = result.get("date")
        # avoid clashing with the imported time module
        appointment_time = result.get("time")

        # Normalise appointment_time to HH:MM:SS so DB time columns accept it
        if appointment_time:
            appointment_time = normalize_time_value(appointment_time)

        # STEP 4 - Tool orchestration (call appointment APIs)
        appointment_result = None

        if intent == "book":
            appointment_result = book_appointment({
                "doctor_name": doctor,
                "date": date,
                "time": appointment_time,
                "patient_name": "Voice User"
            })

        elif intent == "cancel":
            appointment_result = cancel_appointment({
                "doctor_name": doctor,
                "date": date,
                "time": appointment_time,
                "patient_name": "Voice User"
            })

        elif intent == "reschedule":
            appointment_result = reschedule_appointment({
                "doctor_name": doctor,
                "patient_name": "Voice User",
                "date": date,
                "old_time": result.get("old_time"),
                "new_time": result.get("new_time")
            })
        else:
            response_text = "Sorry, I can only help with booking, cancelling or rescheduling appointments right now."
            audio_file = generate_speech(response_text, lang=language)
            return FileResponse(audio_file, media_type="audio/mpeg", filename="response.mp3")

        t_tools = time.time()

        # STEP 6 - Generate response text from appointment_result
        if not isinstance(appointment_result, dict):
            response_text = "Something went wrong while handling your request."
        elif appointment_result.get("error"):
            response_text = f"Sorry, {appointment_result['error']}"
        elif appointment_result.get("message"):
            response_text = appointment_result["message"]
            doctor_name = appointment_result.get("doctor")
            appt_time = appointment_result.get("time")
            if doctor_name and appt_time:
                response_text = f"{response_text} with {doctor_name} at {appt_time}."
        else:
            response_text = "Your request has been processed."

        # STEP 7 - Text to Speech
        audio_file = generate_speech(response_text, lang=language)
        t_tts = time.time()

        # Log latency breakdown in milliseconds
        try:
            latency_logger.info(
                "voice_agent_latency_ms "
                f"stt={ (t_stt - t_start) * 1000:.1f} "
                f"lang={ (t_lang - t_stt) * 1000:.1f} "
                f"agent={ (t_agent - t_lang) * 1000:.1f} "
                f"tools={ (t_tools - t_agent) * 1000:.1f} "
                f"tts={ (t_tts - t_tools) * 1000:.1f} "
                f"total={ (t_tts - t_start) * 1000:.1f}"
            )
        except Exception:
            # Logging should never break the endpoint
            pass

        # STEP 8 - Return audio response
        return FileResponse(audio_file, media_type="audio/mpeg", filename="response.mp3")

    except Exception as e:
        return {"error": str(e)}
    
@app.post("/text-to-speech")
def text_to_speech(data: dict):

    text = data.get("text")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    audio_file = generate_speech(text)

    return FileResponse(audio_file, media_type="audio/mpeg", filename="response.mp3")

@app.post("/detect-language")
def detect_language_api(data: dict):

    text = data.get("text")

    if not text:
        raise HTTPException(status_code=400, detail="Text is required")

    language = detect_language(text)

    return {
        "language": language
    }
@app.post("/memory")
def memory(data: dict):

    session_id = data.get("session_id")
    message = data.get("message")

    if not session_id or not message:
        raise HTTPException(status_code=400, detail="session_id and message required")

    memory_data = {
        "message": message
    }

    store_session(session_id, memory_data)

    return {
        "status": "stored"
    }