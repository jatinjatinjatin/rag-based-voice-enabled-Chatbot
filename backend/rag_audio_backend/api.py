import os
from fastapi import FastAPI, File, UploadFile, HTTPException
from pydantic import BaseModel
import shutil
from dotenv import load_dotenv

# Import from rag_full_pipeline
from rag_full_pipeline import (
    transcribe_audio,
    chunk_text,
    embed_and_store,
    answer_question,
    TRANSCRIPTIONS_DIRECTORY,
    AUDIO_DIRECTORY
)

load_dotenv()

app = FastAPI(title="Audio RAG API", version="1.0")

# Request and Response models
class QueryRequest(BaseModel):
    question: str

class QueryResponse(BaseModel):
    answer: str

# Global state (in-memory; restarts on server restart)
vector_db = None
transcriptions_dict = {}

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Upload and process audio file"""
    global vector_db, transcriptions_dict
    
    # Create directories if needed
    os.makedirs(AUDIO_DIRECTORY, exist_ok=True)
    os.makedirs(TRANSCRIPTIONS_DIRECTORY, exist_ok=True)
    
    # Save uploaded file
    audio_path = os.path.join(AUDIO_DIRECTORY, file.filename)
    with open(audio_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    try:
        # Transcribe the audio
        transcription = transcribe_audio(audio_path, file.filename)
        if not transcription:
            raise HTTPException(status_code=500, detail="Transcription failed")
        
        # Store transcription in memory
        transcriptions_dict[file.filename] = transcription
        
        # Re-chunk all stored transcriptions and rebuild vector DB
        all_chunks = []
        for filename, text in transcriptions_dict.items():
            file_chunks = chunk_text(text, filename)
            all_chunks.extend(file_chunks)
        
        vector_db = embed_and_store(all_chunks)
        
        # Return info about the newly uploaded file
        new_chunks = chunk_text(transcription, file.filename)
        
        return {
            "message": "File uploaded and indexed successfully",
            "filename": file.filename,
            "chunks_created": len(new_chunks),  # Matches frontend expectation
            "total_files_indexed": len(transcriptions_dict)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Query the RAG system with a question"""
    global vector_db, transcriptions_dict
    
    if not vector_db or not transcriptions_dict:
        raise HTTPException(status_code=400, detail="No audio files indexed yet. Upload an audio file first.")
    
    answer = answer_question(vector_db, request.question, transcriptions_dict)
    return QueryResponse(answer=answer)
