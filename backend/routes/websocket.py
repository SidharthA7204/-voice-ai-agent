import time
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# import your services
from services.speech_to_text import transcribe_audio
from services.text_to_speech import generate_speech
from agent.intent_parser import process_user_command

router = APIRouter()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("voice-agent")


@router.websocket("/ws/voice")
async def voice_websocket(websocket: WebSocket):

    await websocket.accept()
    logger.info("Voice client connected")

    try:
        while True:

                    # -----------------------------
            # Receive message from client
            # -----------------------------
            message = await websocket.receive()

            # -----------------------------
            # Start latency measurement
            # -----------------------------
            start_time = time.time()

            # If client sends audio bytes
            if "bytes" in message and message["bytes"] is not None:

                audio_bytes = message["bytes"]

                with open("temp_audio.wav", "wb") as f:
                    f.write(audio_bytes)

                # -----------------------------
                # Speech to Text
                # -----------------------------
                stt_start = time.time()

                user_text = transcribe_audio("temp_audio.wav")

                stt_latency = time.time() - stt_start

            # If client sends text (for testing via WebSocketKing)
            elif "text" in message and message["text"] is not None:

                user_text = message["text"]
                stt_latency = 0

            else:
                continue

            logger.info(f"User said: {user_text}")

            # -----------------------------
            # AI Agent reasoning
            # -----------------------------
            agent_start = time.time()

            agent_response = process_user_command(user_text)

            if isinstance(agent_response, dict):
                response_text = agent_response.get("message", "Okay")
            else:
                response_text = str(agent_response)

            agent_latency = time.time() - agent_start

            logger.info(f"Agent response: {response_text}")

            # -----------------------------
            # Text to Speech
            # -----------------------------
            tts_start = time.time()

            audio_file = generate_speech(response_text)

            tts_latency = time.time() - tts_start

            # -----------------------------
            # Send audio response
            # -----------------------------
            with open(audio_file, "rb") as f:
                audio_output = f.read()

            await websocket.send_bytes(audio_output)

            # -----------------------------
            # Total latency
            # -----------------------------
            total_latency = time.time() - start_time

            logger.info(
                {
                    "stt_latency_ms": round(stt_latency * 1000, 2),
                    "agent_latency_ms": round(agent_latency * 1000, 2),
                    "tts_latency_ms": round(tts_latency * 1000, 2),
                    "total_latency_ms": round(total_latency * 1000, 2),
                }
            )

    except WebSocketDisconnect:
        logger.info("Voice client disconnected")

    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close()