🎙️ Voice AI Agent – Smart Doctor Appointment Assistant

A Voice-Enabled AI Assistant that allows users to book, cancel, and reschedule doctor appointments using voice commands.
The system converts speech to text, understands user intent, interacts with a backend scheduler, and responds with AI-generated voice feedback.

This project demonstrates AI integration, backend engineering, API design, and voice interaction systems.

🚀 Features

✅ Voice command based appointment booking
✅ Automatic speech-to-text processing
✅ AI intent detection for user commands
✅ Doctor schedule management
✅ Appointment booking system
✅ Appointment cancellation
✅ Appointment rescheduling
✅ Language detection support
✅ Text-to-speech response generation
✅ Memory system for conversation context
✅ REST API with interactive documentation

🧠 Example Voice Commands

Users can interact naturally with the assistant:

Book appointment with doctor tomorrow at 4 PM
Cancel my appointment tomorrow
Reschedule my appointment to 6 PM
I want to meet the doctor tomorrow

The AI agent automatically:

1️⃣ Converts voice → text
2️⃣ Detects intent
3️⃣ Calls the correct API
4️⃣ Returns a voice response

🏗️ System Architecture
User Voice
     │
     ▼
Speech-to-Text
     │
     ▼
Intent Detection (AI Agent)
     │
     ▼
Appointment Scheduler
     │
     ▼
Database
     │
     ▼
Text-to-Speech Response
🛠️ Tech Stack
Backend

Python

FastAPI

Uvicorn

AI / NLP

Speech Recognition

Whisper / STT

LangDetect

RapidFuzz (intent matching)

Voice Processing

Speech-to-Text

Text-to-Speech

gTTS

Database

SQLite

Tools

Git & GitHub

REST APIs

Swagger Documentation

📂 Project Structure
voice-ai-agent
│
├── agent
│   └── intent_parser.py
│
├── backend
│   └── routes
│       └── websocket.py
│
├── database
│   └── db.py
│
├── memory
│   └── session_memory.py
│
├── scheduler
│   └── appointment_scheduler.py
│
├── services
│   ├── speech_to_text.py
│   ├── text_to_speech.py
│   └── language_detector.py
│
├── main.py
├── requirements.txt
└── README.md
⚙️ Installation
1️⃣ Clone the repository
git clone https://github.com/SidharthA7204/-voice-ai-agent.git
cd voice-ai-agent
2️⃣ Create virtual environment
python -m venv venv

Activate:

Windows

venv\Scripts\activate
3️⃣ Install dependencies
pip install -r requirements.txt
▶️ Run the Application

Start the FastAPI server:

uvicorn main:app --reload

Server will start at:

http://127.0.0.1:8000
📄 API Documentation

Interactive API docs:

http://127.0.0.1:8000/docs

Available APIs:

Method	Endpoint	Description
GET	/doctors	View doctor schedules
POST	/book-appointment	Book appointment
DELETE	/cancel-appointment	Cancel appointment
PUT	/reschedule-appointment	Reschedule appointment
POST	/ai-agent	Process AI command
POST	/voice-agent	Voice interaction endpoint
POST	/text-to-speech	Convert text to audio
POST	/detect-language	Detect language
POST	/memory	Manage conversation memory
🎤 Voice Workflow

1️⃣ User speaks a command
2️⃣ Speech converted to text
3️⃣ AI detects intent
4️⃣ Scheduler processes request
5️⃣ System responds with generated voice

📊 Example Response
{
 "message": "Appointment booked successfully with Dr. Smith at 4 PM"
}

Audio response is generated for the user.

📈 Future Improvements

🔹 Real-time voice streaming
🔹 Multi-language voice assistant
🔹 Integration with hospital systems
🔹 Authentication system
🔹 Web / mobile interface
🔹 AI conversation assistant

🎯 Learning Outcomes

This project demonstrates:

AI-driven application design

Voice interface systems

FastAPI backend development

API architecture

Natural language command processing

Real-time voice processing

👨‍💻 Author

Sidharth A

GitHub
https://github.com/SidharthA7204
