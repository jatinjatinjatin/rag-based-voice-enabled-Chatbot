# ==============================================================================
# backend.py — GENERAL TEXT CHAT (Groq + ChromaDB)
# ==============================================================================
# Uses:
# - GROQ_API_KEY
# - llama-3.1-8b-instant
# - ChromaDB semantic memory
# ==============================================================================

import os
import uuid
from typing import List, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer

from langchain_groq import ChatGroq

# ==============================================================================
# ENVIRONMENT
# ==============================================================================
load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in .env file")

# ==============================================================================
# GROQ LLM (CORRECT USAGE)
# ==============================================================================
groq_llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    groq_api_key=GROQ_API_KEY,
    temperature=0.3
)

# ==============================================================================
# FASTAPI APP
# ==============================================================================
app = FastAPI(title="General Chat Backend (Groq)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==============================================================================
# CHROMA DB (Semantic Memory)
# ==============================================================================
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

chroma_client = chromadb.Client(
    Settings(
        persist_directory="./general_chroma_db",
        anonymized_telemetry=False
    )
)

collection = chroma_client.get_or_create_collection(
    name="general_chat_memory"
)

# ==============================================================================
# REQUEST SCHEMA
# ==============================================================================
class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]

# ==============================================================================
# SYSTEM PROMPT
# ==============================================================================
SYSTEM_PROMPT = """
You are a helpful, intelligent assistant.

You handle:
- Programming questions (DSA, algorithms, code)
- Computer science concepts
- Logical reasoning
- General learning questions

Rules:
- Be accurate and concise
- Provide correct code when asked
- Explain step-by-step if needed
- If something is unknown, say so honestly
"""

# ==============================================================================
# MEMORY UTILITIES
# ==============================================================================
def embed_text(text: str):
    return embedding_model.encode(text).tolist()

def store_memory(text: str):
    collection.add(
        ids=[str(uuid.uuid4())],
        documents=[text],
        embeddings=[embed_text(text)]
    )

def retrieve_memory(query: str, k: int = 3):
    results = collection.query(
        query_embeddings=[embed_text(query)],
        n_results=k
    )
    return results.get("documents", [[]])[0]

# ==============================================================================
# CHAT ENDPOINT
# ==============================================================================
@app.post("/chat")
def chat(req: ChatRequest):
    try:
        if not req.messages:
            raise HTTPException(status_code=400, detail="No messages provided")

        latest_user_message = req.messages[-1]["content"]

        # 🔹 Retrieve semantic memory
        memories = retrieve_memory(latest_user_message)

        memory_context = ""
        if memories:
            memory_context = "\n\nRelevant past context:\n" + "\n".join(
                f"- {m}" for m in memories
            )

        # 🔹 Build prompt text
        conversation_text = SYSTEM_PROMPT + memory_context + "\n\n"

        for msg in req.messages:
            role = "User" if msg["role"] == "user" else "Assistant"
            conversation_text += f"{role}: {msg['content']}\n"

        # 🔹 CALL GROQ (CORRECT)
        response = groq_llm.invoke(conversation_text)

        answer = response.content.strip()

        # 🔹 Store memory
        store_memory(latest_user_message)
        store_memory(answer)

        return {"response": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

