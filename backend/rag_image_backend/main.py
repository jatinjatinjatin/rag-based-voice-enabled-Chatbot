# ==============================================================================
# SECTION 1: IMPORTS & SYSTEM CONFIGURATION
# ==============================================================================
import os
import shutil
import warnings
import logging
import time
from typing import List

# --- NUCLEAR CLEANUP BLOCK (Suppress Logs) ---
os.environ["ANONYMIZED_TELEMETRY"] = "False"
warnings.filterwarnings("ignore")
logging.getLogger('chromadb.telemetry.product.posthog').setLevel(logging.CRITICAL)
logging.getLogger('chromadb').setLevel(logging.CRITICAL)
logging.getLogger('posthog').setLevel(logging.CRITICAL)
# ---------------------------------------------

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn

from langchain_chroma import Chroma
from chromadb.config import Settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_classic.chains import create_history_aware_retriever, create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.documents import Document
import google.generativeai as genai
from PIL import Image

# ==============================================================================
# SECTION 2: GLOBAL SETUP (KEYS, DB, & CLIENTS)
# ==============================================================================
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")  # Corrected realistic default
DB_PATH = "./chroma_db"
TEMP_IMAGE_FOLDER = "./temp_images"

if not GOOGLE_API_KEY:
    raise ValueError("Error: GOOGLE_API_KEY not found in .env file.")

# Configure Gemini
genai.configure(api_key=GOOGLE_API_KEY)

# Global vision model (used for image analysis during ingest)
vision_model = genai.GenerativeModel(MODEL_NAME)

# Vector DB Connection
embedding_function = GoogleGenerativeAIEmbeddings(
    model="models/text-embedding-004",
    google_api_key=GOOGLE_API_KEY
)

vectorstore = Chroma(
    persist_directory=DB_PATH,
    embedding_function=embedding_function,
    client_settings=Settings(anonymized_telemetry=False)
)

# In-Memory Session Storage (chat history only — vector DB is global/persistent)
chat_sessions = {}

# ==============================================================================
# SECTION 3: AI LOGIC (THE "BRAIN")
# ==============================================================================

def analyze_image_with_retry(image: Image.Image, retries: int = 5) -> str:
    """
    Sends an image to Gemini Vision with a detailed analysis prompt.
    Includes exponential backoff for rate limits / overload.
    Returns the raw text description.
    """
    prompt = (
        "Provide a highly detailed description of this image. Include:"
        "\n- All visible text (extract exactly)"
        "\n- Objects, people, animals, scene composition"
        "\n- Colors, lighting, layout, and style"
        "\n- Any charts, tables, diagrams, or data"
        "\n- Overall meaning or context if apparent"
        "\nBe thorough and descriptive."
    )

    for attempt in range(retries):
        try:
            response = vision_model.generate_content([prompt, image])
            return response.text.strip()
        except Exception as e:
            error_str = str(e).lower()
            if any(code in error_str for code in ["429", "503", "quota", "resource_exhausted"]):
                sleep_time = 2 ** attempt
                time.sleep(sleep_time)
                continue
            raise HTTPException(status_code=500, detail=f"Gemini Vision error: {str(e)}")
    
    raise HTTPException(status_code=500, detail="Gemini API overloaded after multiple retries.")

def build_rag_chain():
    """Constructs the LangChain retrieval QA pipeline."""
    llm = ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})  # Slightly increased for multi-image cases

    # History-aware contextualizer
    contextualize_prompt = ChatPromptTemplate.from_messages([
        ("system", "Given the chat history and the latest user question, "
         "rephrase the question into a standalone question that can be understood "
         "without the history. Do NOT answer the question, just rephrase it."),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])

    history_aware_retriever = create_history_aware_retriever(
        llm, retriever, contextualize_prompt
    )

    # QA prompt
    qa_prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert image analyst. Answer the question using ONLY "
         "the following retrieved context about the image(s). If the context does not "
         "contain relevant information, say 'I don't have enough information.'\n\n"
         "Context:\n{context}"),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}")
    ])

    question_answer_chain = create_stuff_documents_chain(llm, qa_prompt)
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

    return rag_chain

# ==============================================================================
# SECTION 4: API ENDPOINTS (THE INTERFACE)
# ==============================================================================

app = FastAPI(title="Image RAG API (Gemini Vision)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatInput(BaseModel):
    session_id: str
    message: str

@app.get("/")
def health_check():
    return {"status": "online", "model": MODEL_NAME, "db_path": DB_PATH}

@app.post("/ingest")
async def upload_images(files: List[UploadFile] = File(...)):
    """Upload → Analyze with Gemini Vision → Index descriptions into Chroma"""
    os.makedirs(TEMP_IMAGE_FOLDER, exist_ok=True)

    processed = 0
    errors = []

    for file in files:
        temp_path = None
        img = None
        try:
            # Save temporarily
            temp_path = os.path.join(TEMP_IMAGE_FOLDER, file.filename)
            with open(temp_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            # Open with PIL
            img = Image.open(temp_path)

            # Analyze
            description = analyze_image_with_retry(img)

            # Create and index document
            doc = Document(
                page_content=description,
                metadata={"source": file.filename}
            )
            vectorstore.add_documents([doc])
            processed += 1

        except Exception as e:
            errors.append(f"{file.filename}: {str(e)}")
        finally:
            # ALWAYS close the image and remove temp file (critical on Windows)
            if img is not None:
                img.close()
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception as remove_error:
                    errors.append(f"Cleanup failed for {file.filename}: {str(remove_error)}")

    return {
        "message": f"Successfully processed {processed}/{len(files)} images",
        "errors": errors
    }

@app.post("/chat")
async def chat(request: ChatInput):
    """Chat with the indexed images (history-aware RAG)"""
    session_id = request.session_id
    if session_id not in chat_sessions:
        chat_sessions[session_id] = []

    try:
        chain = build_rag_chain()
        result = chain.invoke({
            "input": request.message,
            "chat_history": chat_sessions[session_id]
        })

        answer = result["answer"]

        # Update session history
        chat_sessions[session_id].extend([
            HumanMessage(content=request.message),
            AIMessage(content=answer)
        ])

        return {"response": answer}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))