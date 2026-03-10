# Voice AI Appointment Agent

An AI-powered voice assistant that allows users to manage appointments using natural voice commands.  
The system converts speech into text, processes the intent, performs backend actions, and responds with synthesized speech.

This project demonstrates an **Agentic AI workflow** where voice input triggers automated backend actions through an intelligent processing pipeline.

## Live Demo

Try the working application here:
LIVE_DEMO_LINK:https://voice-ai-agent-xtfx.onrender.com/docs

## Demo Video

Watch the system working with real voice commands.

VIDEO_LINK:https://drive.google.com/file/d/1xI_dw11TQyMBtlgLnMJ5-8cbrwzskhiO/view

---

## Features

• Voice-based interaction with the system  
• Book, cancel, and reschedule appointments using natural language  
• Real-time speech-to-text transcription  
• AI-based intent recognition  
• Backend appointment scheduling logic  
• Text-to-speech audio responses  
• REST API-based backend architecture

---

## System Architecture
User Voice
↓
Speech-to-Text
↓
Intent Processing / Command Parsing
↓
Appointment Scheduler API
↓
Database
↓
Text-to-Speech
↓
Audio Response


---

## Tech Stack

### Backend
- Python
- FastAPI

### AI & Voice Processing
- Speech-to-Text
- Text-to-Speech
- Natural Language Command Parsing

### Database
- SQL / PostgreSQL (if used)

### Tools
- Git
- Postman
- VS Code

---
## Example Voice Commands

Book appointment:Book an appointment with Doctor Albert tomorrow at 4 PM
Cancel appointment:Cancel my appointment with Doctor Albert tomorrow
Reschedule appointment:Move my appointment with Doctor Albert to Friday at 5 PM


---

## API Workflow

1. User speaks a command
2. Audio is converted into text using Speech-to-Text
3. The command is processed by an intent parser
4. Backend scheduling API executes the action
5. System generates response
6. Response is converted into speech using Text-to-Speech

---

## Project Structure
voice-ai-agent
│
├── agent
│ └── intent_parser.py
│
├── services
│ ├── speech_to_text.py
│ └── text_to_speech.py
│
├── database
│ └── db.py
│
├── main.py
│
└── requirements.txt


---

## How to Run the Project

### 1 Install dependencies
pip install -r requirements.txt


### 2 Start the server
uvicorn main:app --reload


### 3 Test APIs

Use Postman or curl to send audio requests.

---

## Future Improvements

• Integrate LLM-based intent understanding  
• Add multi-user authentication  
• Add calendar integrations (Google Calendar)  
• Implement vector search for contextual memory  
• Deploy as real-time voice assistant

---

## Author

Sidharth A  
Full Stack Developer | AI Systems Enthusiast

GitHub: https://github.com/SidharthA7204
## Demo Video

Watch the working demo of the Voice AI Appointment Agent:

https://youtu.be/YOUR_VIDEO_LINK


