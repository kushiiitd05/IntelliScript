from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
import asyncio
from typing import Optional
from pydantic import BaseModel
import uuid
import json

from services.video_processor import VideoProcessor
from services.audio_processor import AudioProcessor
from services.transcription_service import TranscriptionService
from services.diarization_service import DiarizationService
from services.summarization_service import SummarizationService
from services.qa_service import QAService
from services.export_service import ExportService
from utils.cache_manager import CacheManager
from utils.progress_tracker import ProgressTracker

app = FastAPI(title="IntelliScript API", version="1.0.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
cache_manager = CacheManager()
progress_tracker = ProgressTracker()

class ProcessingRequest(BaseModel):
    session_id: str
    url: Optional[str] = None
    language: str = "en"

class QuestionRequest(BaseModel):
    session_id: str
    question: str

@app.get("/")
async def root():
    return {"message": "IntelliScript API is running"}

@app.post("/api/upload")
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """Handle video file upload"""
    try:
        # Generate session ID
        session_id = str(uuid.uuid4())
        
        # Save uploaded file
        upload_dir = f"uploads/{session_id}"
        os.makedirs(upload_dir, exist_ok=True)
        
        file_path = os.path.join(upload_dir, file.filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Start background processing
        background_tasks.add_task(process_video_file, session_id, file_path)
        
        return {"session_id": session_id, "status": "uploaded"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/process-url")
async def process_youtube_url(request: ProcessingRequest, background_tasks: BackgroundTasks):
    """Handle YouTube URL processing"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        
        # Start background processing
        background_tasks.add_task(process_video_url, session_id, request.url, request.language)
        
        return {"session_id": session_id, "status": "processing"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    """Get processing progress"""
    progress = progress_tracker.get_progress(session_id)
    return progress

@app.get("/api/results/{session_id}")
async def get_results(session_id: str):
    """Get processing results"""
    try:
        results_path = f"results/{session_id}/results.json"
        if not os.path.exists(results_path):
            return {"status": "processing", "results": None}
        
        with open(results_path, 'r', encoding='utf-8') as f:
            results = json.load(f)
        
        return {"status": "completed", "results": results}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get results: {str(e)}")

@app.post("/api/ask")
async def ask_question(request: QuestionRequest):
    """Handle Q&A requests"""
    try:
        qa_service = QAService()
        answer = await qa_service.answer_question(request.session_id, request.question)
        return {"answer": answer}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Q&A failed: {str(e)}")

@app.get("/api/export/{session_id}/{format}")
async def export_results(session_id: str, format: str):
    """Export results in various formats"""
    try:
        export_service = ExportService()
        file_path = await export_service.export_results(session_id, format)
        
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Export file not found")
        
        return FileResponse(
            file_path,
            media_type='application/octet-stream',
            filename=os.path.basename(file_path)
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

async def process_video_file(session_id: str, file_path: str):
    """Background task for processing video file"""
    try:
        progress_tracker.update_progress(session_id, "Extracting audio...", 10)
        
        # Extract and clean audio
        audio_processor = AudioProcessor()
        audio_path = await audio_processor.extract_and_clean_audio(file_path)
        
        progress_tracker.update_progress(session_id, "Transcribing with Whisper...", 30)
        
        # Transcribe audio
        transcription_service = TranscriptionService()
        whisper_result = await transcription_service.transcribe(audio_path)
        
        progress_tracker.update_progress(session_id, "Analyzing speaker moments...", 60)
        
        # Speaker diarization
        diarization_service = DiarizationService()
        diarization_result = await diarization_service.diarize(audio_path)
        
        progress_tracker.update_progress(session_id, "Generating summary...", 80)
        
        # Generate summary
        summarization_service = SummarizationService()
        summary = await summarization_service.summarize(whisper_result['text'])
        
        progress_tracker.update_progress(session_id, "Finalizing results...", 90)
        
        # Prepare final results
        results = {
            "transcript": whisper_result,
            "diarization": diarization_result,
            "summary": summary,
            "video_path": file_path,
            "audio_path": audio_path
        }
        
        # Save results
        results_dir = f"results/{session_id}"
        os.makedirs(results_dir, exist_ok=True)
        
        with open(f"{results_dir}/results.json", 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2)
        
        progress_tracker.update_progress(session_id, "Complete!", 100)
        
    except Exception as e:
        progress_tracker.update_progress(session_id, f"Error: {str(e)}", -1)

async def process_video_url(session_id: str, url: str, language: str):
    """Background task for processing YouTube URL"""
    try:
        progress_tracker.update_progress(session_id, "Downloading video...", 5)
        
        # Download video
        video_processor = VideoProcessor()
        video_path = await video_processor.download_video(url)
        
        # Continue with same processing as file upload
        await process_video_file(session_id, video_path)
        
    except Exception as e:
        progress_tracker.update_progress(session_id, f"Error: {str(e)}", -1)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)