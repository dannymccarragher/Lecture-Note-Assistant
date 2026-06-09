import uuid
import os
from dotenv import load_dotenv
from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from services.whisper_service import transcribe_audio
from services.llm_service import generate_summary_and_quiz
from services.vector_service import embed_and_store, semantic_search

load_dotenv()

app = FastAPI(title="Lecture Note Assistant")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".mp3", ".mp4", ".wav", ".m4a", ".webm", ".ogg"}

# In-memory store: {lecture_id: {status, filename, transcript, summary, ...}}
lectures: dict = {}


class SearchRequest(BaseModel):
    lecture_id: str
    query: str


async def run_pipeline(lecture_id: str, file_bytes: bytes, filename: str):
    try:
        lectures[lecture_id]["status"] = "transcribing"
        transcript = await transcribe_audio(file_bytes, filename)

        lectures[lecture_id]["status"] = "summarizing"
        llm_result = await generate_summary_and_quiz(transcript)

        lectures[lecture_id]["status"] = "indexing"
        await embed_and_store(lecture_id, transcript)

        lectures[lecture_id].update({
            "status": "complete",
            "transcript": transcript,
            "summary": llm_result["summary"],
            "key_points": llm_result["key_points"],
            "quiz": llm_result["quiz"],
        })
    except Exception as e:
        lectures[lecture_id]["status"] = "error"
        lectures[lecture_id]["error"] = str(e)


# Accepts an audio file, validates the extension, and kicks off the processing
# pipeline in the background. Returns a lecture_id the frontend uses to poll status.
@app.post("/api/upload")
async def upload_lecture(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}")

    lecture_id = str(uuid.uuid4())
    file_bytes = await file.read()

    lectures[lecture_id] = {"status": "processing", "filename": file.filename}
    background_tasks.add_task(run_pipeline, lecture_id, file_bytes, file.filename)

    return {"lecture_id": lecture_id, "status": "processing"}


# Returns the current processing status for a lecture. While the pipeline is
# running, only metadata is returned. Once complete, the full result is included.
@app.get("/api/status/{lecture_id}")
async def get_status(lecture_id: str):
    if lecture_id not in lectures:
        raise HTTPException(status_code=404, detail="Lecture not found")
    job = lectures[lecture_id]
    # Return only metadata fields while still processing
    if job["status"] != "complete":
        return {"status": job["status"], "filename": job.get("filename"), "error": job.get("error")}
    return job


# Takes a natural language query and a lecture_id, runs semantic search over
# the stored transcript chunks, and returns a grounded answer with source segments.
@app.post("/api/search")
async def search(request: SearchRequest):
    job = lectures.get(request.lecture_id)
    if not job:
        raise HTTPException(status_code=404, detail="Lecture not found")
    if job["status"] != "complete":
        raise HTTPException(status_code=400, detail=f"Lecture not ready (status: {job['status']})")

    result = await semantic_search(request.lecture_id, request.query)
    return result


@app.get("/")
async def root():
    return {"message": "Lecture Note Assistant API is running"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
