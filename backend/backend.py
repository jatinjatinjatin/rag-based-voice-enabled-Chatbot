import subprocess
import sys
import time
import os
import signal

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

SERVERS = [
    {
        "name": "PDF",
        "cmd": ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload", "--reload-dir", "."],
        "cwd": os.path.join(BASE_DIR, "rag_pdf_backend"),
    },
    {
        "name": "SQL",
        "cmd": ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload", "--reload-dir", "."],
        "cwd": os.path.join(BASE_DIR, "rag_sql_backend"),
    },
    {
        "name": "Audio",
        "cmd": ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "8002", "--reload", "--reload-dir", "."],
        "cwd": os.path.join(BASE_DIR, "rag_audio_backend"),
    },
    {
        "name": "Video",
        "cmd": ["uvicorn", "video2text:app", "--host", "0.0.0.0", "--port", "8003", "--reload", "--reload-dir", "."],
        "cwd": os.path.join(BASE_DIR, "rag_video_backend"),
    },
    {
        "name": "Image",
        "cmd": ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8004", "--reload", "--reload-dir", "."],
        "cwd": os.path.join(BASE_DIR, "rag_image_backend"),
    },
    {
        "name": "General",
        "cmd": ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8005", "--reload", "--reload-dir", "."],
        "cwd": os.path.join(BASE_DIR, "rag_general_backend"),
    },
]

processes = []

def start_servers():
    print("\n🚀 Starting ALL backends (per-folder .env + safe reload)\n")

    for srv in SERVERS:
        print(f"▶ {srv['name']} → {' '.join(srv['cmd'])}")
        p = subprocess.Popen(
            srv["cmd"],
            cwd=srv["cwd"],     # ✅ critical
            shell=True,         # Windows
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(p)
        time.sleep(1)

    print("\n✅ ALL BACKENDS RUNNING")
    print("♻ Reload ENABLED (SAFE MODE)")
    print("🛑 CTRL + C to stop everything\n")

def stop_servers():
    print("\n🛑 Shutting down all servers...")
    for p in processes:
        try:
            p.send_signal(signal.CTRL_BREAK_EVENT)
        except Exception:
            p.terminate()

if __name__ == "__main__":
    try:
        start_servers()
        for p in processes:
            p.wait()
    except KeyboardInterrupt:
        stop_servers()
