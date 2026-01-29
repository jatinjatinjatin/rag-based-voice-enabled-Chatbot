from fastapi import FastAPI, UploadFile, File, HTTPException
from models import Query
from rag import upload_files, get_chat_response
from utils import check_internet

app = FastAPI(title="Multi-File RAG Chatbot Backend")

@app.post("/upload-files")
async def upload_endpoint(files: list[UploadFile] = File(...)):
    return await upload_files(files)

@app.post("/chat")
async def chat_endpoint(query: Query):
    online = check_internet()
    mode = "online" if online else "offline"
    response = await get_chat_response(query.query, online)
    return {"response": response, "mode": mode}
