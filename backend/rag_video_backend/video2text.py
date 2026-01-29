from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import os
import tempfile
import subprocess
from groq import Groq

# =========================
# CONFIG
# =========================
os.environ["GROQ_API_KEY"] = "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"

FFMPEG_PATH = r"C:\Users\lenovo\Downloads\ffmpeg-8.0.1-essentials_build\ffmpeg-8.0.1-essentials_build\bin\ffmpeg.exe"

client = Groq()
app = FastAPI(title="Video Transcription + Q&A Service")

# =========================
# SCHEMAS
# =========================
class VideoQuery(BaseModel):
    question: str
    context: str

# =========================
# HEALTH CHECK
# =========================
@app.get("/")
def health():
    return {"status": "ok"}

# =========================
# VIDEO → AUDIO → TEXT
# =========================
@app.post("/transcribe")
async def transcribe_video(file: UploadFile = File(...)):
    video_path = None
    audio_path = None

    try:
        # Save video
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as v:
            v.write(await file.read())
            video_path = v.name

        # Prepare audio file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as a:
            audio_path = a.name

        # Extract audio
        cmd = [
            FFMPEG_PATH, "-y",
            "-i", video_path,
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            audio_path
        ]

        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=result.stderr)

        if os.path.getsize(audio_path) == 0:
            return {"text": "[No audio detected in the video]"}

        # Transcribe
        with open(audio_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=("audio.wav", audio_file.read()),
                model="whisper-large-v3-turbo"
            )

        text = getattr(transcription, "text", "").strip()
        if not text:
            text = "[No clear speech detected in the video]"

        return {"text": text}

    finally:
        if video_path and os.path.exists(video_path):
            os.remove(video_path)
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)

# =========================
# VIDEO → QUESTION / SUMMARY
# =========================
@app.post("/query")
def query_video(data: VideoQuery):
    if not data.context.strip():
        return {"answer": "No video transcript available."}

    prompt = f"""
You are an assistant analyzing a video transcript.

Transcript:
{data.context}

User question:
{data.question}

Answer clearly and concisely.
"""

    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )

    return {
        "answer": response.choices[0].message.content.strip()
    }
