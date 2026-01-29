import requests
import os

def check_internet(timeout: int = 4) -> bool:
    try:
        requests.get("https://api.groq.com", timeout=timeout)
        return True
    except Exception:
        return False

def setup_environment_paths():
    """Add Poppler and Tesseract to PATH (Windows-focused, but safe on other OS)"""
    from config import POPPLER_PATH, TESSERACT_PATH
    
    if os.path.exists(POPPLER_PATH):
        os.environ["PATH"] += os.pathsep + POPPLER_PATH
    
    if os.path.exists(TESSERACT_PATH):
        tessdata = os.path.join(TESSERACT_PATH, "tessdata")
        if os.path.exists(os.path.join(TESSERACT_PATH, "tesseract.exe")) and os.path.exists(tessdata):
            os.environ["PATH"] += os.pathsep + TESSERACT_PATH
            os.environ["TESSDATA_PREFIX"] = tessdata
