import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_ollama import ChatOllama

# Load environment variables from .env
load_dotenv()


# Embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-large-en-v1.5"
)

# ---- GROQ LLM (NO HARD-CODED KEY) ----
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is not set in .env file")

groq_llm = ChatGroq(
    model_name="llama-3.1-8b-instant",
    groq_api_key=GROQ_API_KEY,
    temperature=0.3
)

# ---- OLLAMA LLM ----
ollama_llm = ChatOllama(
    model="phi3",
    temperature=0.3,
    num_ctx=8192
)


POPPLER_PATH = r"C:\Users\lenovo\Downloads\Release-25.12.0-0\poppler-25.12.0\Library\bin"
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR"
