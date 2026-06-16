# Lecture Note Assistant

This repository contains a React + Vite frontend and a FastAPI backend for uploading lecture audio/video, processing transcription, generating summaries/quizzes, and searching the lecture content.

## Project structure

- `backend/` — FastAPI server and Python services
- `frontend/` — React + Vite application

## Prerequisites

- Node.js and npm installed
- Python 3.11+ installed
- `ffmpeg` installed and available on `PATH` (required by audio transcription)
- A Groq API key for the backend

## Backend setup

1. Open a terminal and navigate to the backend folder:

```bash
cd backend
```

2. Create and activate a Python virtual environment:

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows CMD:

```cmd
python -m venv .venv
.\.venv\Scripts\activate.bat
```

3. Install Python dependencies:

```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the `backend/` folder with your Groq API key:

```text
GROQ_API_KEY=your_groq_api_key_here
```

5. Start the backend server:

```bash
python main.py
```

The backend will run on `http://127.0.0.1:8000`.

## Frontend setup

1. Open a separate terminal and navigate to the frontend folder:

```bash
cd frontend
```

2. Install npm dependencies:

```bash
npm install
```

3. Start the Vite development server:

```bash
npm run dev
```

The frontend will normally run at `http://localhost:5173`.

## How to use

1. Open the frontend in your browser.
2. Upload a supported audio or video lecture file.
3. The app will create a lecture job, then poll the backend for progress.
4. When processing completes, transcript, summary, quiz, and search features become available.

## Supported file types

Currently the frontend accepts audio/video uploads only:

- `.mp3`
- `.mp4`
- `.wav`
- `.m4a`
- `.webm`
- `.ogg`
- `.mov`
- `.avi`
- `.flac`
- `.aac`
- `.mkv`
- `.mpg`
- `.mpeg`

## Notes

- The backend uses `faster-whisper` for transcription, which requires `ffmpeg`.
- The backend also uses the Groq API for summary and quiz generation.
- If the frontend cannot reach the backend, confirm that the backend is running at `http://127.0.0.1:8000` and that `frontend/src/App.tsx` is configured with the correct `backendUrl`.
