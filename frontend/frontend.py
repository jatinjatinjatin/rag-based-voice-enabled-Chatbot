# ==============================================================================
# frontend.py - MERGED IMAGE SECTION (single tab "Images" handling both quick description + RAG)
# ==============================================================================
# - Removed separate "Image → Text" tab
# - Single "Images" tab: multi-upload + index for RAG, plus "Quick Description" button for single image
# - Added "🆕 New Chat" button at top of sidebar (bottom-left area when sidebar expanded)
# - On "New Chat": resets chat messages, video transcript, image chat history (via new session_id), SQL result/query
# - All other parts unchanged
# ==============================================================================

import streamlit as st
import requests
import sounddevice as sd
import wavio
import os
import tempfile
import time  # ← NEW: for unique image session IDs
from faster_whisper import WhisperModel
import pyttsx3
import pandas as pd
import matplotlib.pyplot as plt

# ────────────────────────────────────────────────
#          API BASE URLS  —  change ports if needed
# ────────────────────────────────────────────────
RAG_PDF_BACKEND   = "http://localhost:8000"     # Documents / PDF RAG
SQL_BACKEND       = "http://localhost:8001"     # SQL natural language queries
AUDIO_RAG_BACKEND = "http://localhost:8002"     # Audio transcription + RAG
VIDEO_BACKEND     = "http://localhost:8003"     # Video to text (Groq Whisper)
IMAGE_BACKEND     = "http://localhost:8004"     # Image RAG (Gemini Vision)
GENERAL_BACKEND   = "http://localhost:8005"     # ← NEW - General chat with Grok

# ============================
# PAGE CONFIG & STYLING
# ============================
st.set_page_config(
    page_title="RAG + SQL + Audio + Video + Image + General Chatbot",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {font-size: 3.2rem; text-align: center; color: #4A90E2; margin-bottom: 0.4rem;}
    .sub-header  {font-size: 1.3rem; text-align: center; color: #7F8C8D; margin-bottom: 1.8rem;}
    .sidebar-header {font-size: 1.6rem; color: #4A90E2; text-align: center; margin-bottom: 0.8rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-header'>🗣️ RAG Multimodal Chatbot</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub-header'>General chat • Documents • Database • Audio • Video • Images • Voice input</p>", unsafe_allow_html=True)

# ============================
# LOAD WHISPER (CACHED) - for voice input
# ============================
@st.cache_resource
def load_whisper():
    return WhisperModel("base", device="cpu", compute_type="int8")

whisper_model = load_whisper()

# ============================
# HELPER FUNCTIONS
# ============================
def record_audio(duration=10, fs=44100):
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1)
    sd.wait()
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        wavio.write(tmp.name, recording, fs, sampwidth=2)
        return tmp.name

def transcribe_audio(audio_path):
    segments, _ = whisper_model.transcribe(audio_path, language="en")
    text = " ".join(seg.text for seg in segments).strip()
    os.unlink(audio_path)
    return text

def speak_response(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty("rate", 180)
        engine.say(text)
        engine.runAndWait()
        engine.stop()
    except RuntimeError:
        pass

# ============================
# DISPLAY MESSAGE FUNCTION (handles text + rich SQL)
# ============================
def display_message(msg: dict):
    """Display a chat message. Supports rich SQL display with table, download & charts."""
    if msg.get("rich_type") == "sql" and msg.get("rich_data"):
        rich = msg["rich_data"]
        st.markdown("**Generated SQL Query:**")
        st.code(rich.get("sql", "No SQL returned"), language="sql")

        rows = rich.get("rows", [])
        if rows:
            df = pd.DataFrame(rows)
            st.markdown("**Query Results:**")
            st.dataframe(df, use_container_width=True)

            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download results as CSV",
                data=csv_data,
                file_name="sql_results.csv",
                mime="text/csv",
                use_container_width=True
            )

            # ───── Visualization ─────
            st.markdown("**Visualization:**")
            numeric_cols = df.select_dtypes(include="number").columns.tolist()
            categorical_cols = [c for c in df.columns if c not in numeric_cols]

            if categorical_cols and numeric_cols:
                cat_col = categorical_cols[0]
                num_col = numeric_cols[0]

                # Bar chart
                bar_data = df[[cat_col, num_col]].dropna().set_index(cat_col)
                if len(bar_data) > 1:
                    st.bar_chart(bar_data)

                # Pie chart (only if reasonable number of categories)
                if 2 <= df[cat_col].nunique() <= 12:
                    pie_data = df.groupby(cat_col)[num_col].sum()
                    fig, ax = plt.subplots(figsize=(8, 6))
                    ax.pie(pie_data.values, labels=pie_data.index, autopct='%1.1f%%', startangle=90)
                    ax.axis('equal')
                    ax.set_title(f"{num_col} by {cat_col}")
                    st.pyplot(fig)
                    plt.close(fig)

            elif len(numeric_cols) >= 2:
                st.line_chart(df[numeric_cols])

            elif len(numeric_cols) == 1:
                st.bar_chart(df[numeric_cols])

        else:
            st.info("The query returned no rows.")

        # Optional short summary caption
        if msg["content"]:
            st.caption(msg["content"])

    else:
        # Fallback for normal text messages
        st.markdown(msg["content"])

# ============================
# SIDEBAR: NEW CHAT BUTTON + UPLOAD SECTIONS
# ============================
with st.sidebar:
    # New Chat button at the top (visible in bottom-left area when sidebar is open)
    if st.button("🆕 New Chat", use_container_width=True, type="primary"):
        st.session_state.messages = []
        st.session_state.last_spoken = None
        st.session_state.video_transcript = ""
        st.session_state.sql_result = None
        st.session_state.sql_current_query = ""
        st.session_state.image_session_id = f"image_session_{int(time.time())}"
        st.rerun()

    st.markdown("<h3 class='sidebar-header'>📁 Upload Files</h3>", unsafe_allow_html=True)

    tab_doc, tab_images, tab_sql, tab_audio_rag, tab_video = st.tabs(
        ["Documents", "Images", "SQL / CSV", "Audio → RAG", "Video → Text"]
    )

    # Documents (RAG)
    with tab_doc:
        docs = st.file_uploader("PDF / TXT / CSV", type=["pdf", "txt", "csv"], accept_multiple_files=True)
        if docs and st.button("Index Documents"):
            files_data = [("files", (f.name, f.getvalue())) for f in docs]
            try:
                r = requests.post(f"{RAG_PDF_BACKEND}/upload-files", files=files_data, timeout=300)
                if r.status_code == 200:
                    st.success(r.json().get("status", "Indexed"))
                else:
                    st.error(f"Upload failed: {r.status_code} - {r.text}")
            except Exception as e:
                st.error(f"Connection failed: {e}")

    # Images (MERGED: handles multi-RAG + single quick description)
    with tab_images:
        st.caption("Upload one or more images → analyze with Gemini Vision → index for questions in chat mode")
        uploaded_images = st.file_uploader(
            "Upload Images",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="image_upload"
        )
        
        if uploaded_images:
            cols = st.columns(3)
            for i, img in enumerate(uploaded_images):
                with cols[i % 3]:
                    st.image(img, caption=img.name)
        
        if uploaded_images and st.button("Analyze & Index Images", use_container_width=True):
            with st.spinner("Analyzing with Gemini Vision and indexing... (may take time)"):
                files = [("files", (file.name, file.getvalue(), file.type)) for file in uploaded_images]
                try:
                    r = requests.post(f"{IMAGE_BACKEND}/ingest", files=files, timeout=300)
                    r.raise_for_status()
                    result = r.json()
                    st.success(result.get("message", "Indexed successfully!"))
                    if result.get("errors"):
                        st.warning("Some files failed: " + "; ".join(result["errors"]))
                except Exception as e:
                    st.error(f"Indexing failed: {e}")

        # Quick description for single image
        if uploaded_images and len(uploaded_images) == 1:
            st.markdown("---")
            st.subheader("Quick Description (Single Image)")
            if st.button("Generate Detailed Description", use_container_width=True):
                with st.spinner("Analyzing image with Gemini Vision..."):
                    try:
                        # Ingest
                        files = [("files", (uploaded_images[0].name, uploaded_images[0].getvalue(), uploaded_images[0].type))]
                        r_ingest = requests.post(f"{IMAGE_BACKEND}/ingest", files=files, timeout=300)
                        r_ingest.raise_for_status()

                        # Chat for description (uses current image session)
                        payload = {
                            "session_id": st.session_state.image_session_id,
                            "message": "Provide a highly detailed description of this image."
                        }
                        r_chat = requests.post(f"{IMAGE_BACKEND}/chat", json=payload, timeout=240)
                        r_chat.raise_for_status()
                        description = r_chat.json().get("response", "No description returned.")

                        st.markdown("**Detailed Description:**")
                        st.markdown(description)
                    except Exception as e:
                        st.error(f"Failed to generate description: {e}")

    # SQL / CSV
    with tab_sql:
        csv = st.file_uploader("CSV file", type=["csv"])
        if csv and st.button("Upload to DB"):
            try:
                files = {"file": (csv.name, csv.getvalue(), csv.type)}
                r = requests.post(f"{SQL_BACKEND}/api/upload_csv", files=files, timeout=240)
                if r.status_code == 200:
                    d = r.json()
                    st.success(f"Table **{d.get('table')}** • {d.get('rows_inserted')} rows")
                    if d.get("columns"):
                        st.write("**Columns:**")
                        st.write(d["columns"])
                else:
                    st.error(r.text)
            except Exception as e:
                st.error(f"SQL error: {e}")

    # Audio → RAG
    with tab_audio_rag:
        st.caption("Upload audio → transcribe → ask questions")
        af = st.file_uploader("Audio", type=["wav","mp3","m4a","ogg"])
        if af and st.button("Transcribe & Index"):
            with st.spinner("Processing..."):
                try:
                    files = {"file": (af.name, af.getvalue(), af.type)}
                    r = requests.post(f"{AUDIO_RAG_BACKEND}/upload", files=files, timeout=180)
                    r.raise_for_status()
                    d = r.json()
                    st.success(f"Indexed • {d.get('chunks_created', '?')} chunks")
                except Exception as e:
                    st.error(f"Error: {e}")

    # Video → Text
    with tab_video:
        st.caption("Upload video → transcribe to text → ask questions about content")
        vf = st.file_uploader("Video file", type=["mp4", "mov", "avi", "mkv"])
        if vf and st.button("Transcribe Video"):
            with st.spinner("Sending video to transcription service... (may take time)"):
                try:
                    files = {"file": (vf.name, vf.getvalue(), vf.type)}
                    r = requests.post(f"{VIDEO_BACKEND}/transcribe", files=files, timeout=300)
                    r.raise_for_status()
                    result = r.json()
                    transcript = result.get("text", result.get("response", "No text returned"))
                    
                    st.session_state.video_transcript = transcript
                    
                    st.success("Video transcribed successfully!")
                    st.markdown("**Transcription preview:**")
                    st.text_area("Text", transcript, height=200)
                except Exception as e:
                    st.error(f"Transcription failed: {e}")

# ============================
# SESSION STATE
# ============================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_spoken" not in st.session_state:
    st.session_state.last_spoken = None
if "video_transcript" not in st.session_state:
    st.session_state.video_transcript = ""

# Image session ID (for resetting chat history on new chat)
st.session_state.setdefault("image_session_id", "default_session")

# SQL-specific session state
st.session_state.setdefault("sql_history", [])
st.session_state.setdefault("sql_saved_dashboards", {})
st.session_state.setdefault("sql_result", None)
st.session_state.setdefault("sql_current_query", "")

# ============================
# SIDEBAR: SQL HISTORY & SAVED (visible only in SQL mode)
# ============================
use_specialized = st.checkbox("🔧 Enable Specialized RAG Modes (PDF, SQL, Audio, Video, Images)", key="use_specialized_checkbox")

if use_specialized:
    mode = st.radio(
        "Select mode:",
        ["Documents (PDFs)", "Database (SQL)", "Transcribed Audio", "Transcribed Video", "Images"],
        horizontal=True
    )
else:
    mode = "General"

if mode == "Database (SQL)":
    with st.sidebar:
        st.subheader("🕒 Query History")
        for i, q in enumerate(reversed(st.session_state.sql_history[-10:])):
            if st.button(q, key=f"sql_hist_{i}"):
                st.session_state.sql_current_query = q
                st.rerun()

        st.subheader("📌 Saved Dashboards")
        for i, name in enumerate(st.session_state.sql_saved_dashboards):
            if st.button(name, key=f"sql_saved_{i}"):
                st.session_state.sql_current_query = st.session_state.sql_saved_dashboards[name]
                st.rerun()

# ============================
# MODE SELECTION
# ============================
st.markdown("### 💬 Chat Mode")
if not use_specialized:
    st.success("🧠 **General Chat Mode Active** –  Ask anything (code, explanations, reasoning, fun questions, etc.)")

# ============================
# MAIN CONTENT
# ============================
if mode == "Database (SQL)":
    st.markdown("### 📊 SQL Agent Dashboard")
    st.info("💡 **First:** Upload a CSV file in the sidebar ('SQL / CSV' tab). **Then:** Ask natural language questions about your data (e.g., 'total sales by region').")

    query = st.text_input(
        "Ask your data:",
        value=st.session_state.sql_current_query,
        placeholder="e.g., total sales by region, average salary by department, top 10 customers"
    )

    col1, col2, col3 = st.columns([1, 1, 2])
    run_btn = col1.button("🚀 Run", use_container_width=True)
    save_btn = col2.button("📌 Save", use_container_width=True)
    chart_type = col3.selectbox("📊 Chart", ["Auto", "Bar", "Line", "Area", "Pie"])

    if save_btn and query.strip():
        name = f"Dashboard {len(st.session_state.sql_saved_dashboards) + 1}"
        st.session_state.sql_saved_dashboards[name] = query
        st.success(f"Saved as '{name}'")
        st.rerun()

    if run_btn and query.strip():
        with st.spinner("Thinking..."):
            try:
                r = requests.post(f"{SQL_BACKEND}/api/sql", json={"prompt": query}, timeout=240)
                if r.status_code == 200:
                    st.session_state.sql_result = r.json()
                    if query not in st.session_state.sql_history:
                        st.session_state.sql_history.append(query)
                    st.session_state.sql_current_query = query
                else:
                    st.error(f"Backend error: {r.text}")
                    st.session_state.sql_result = None
            except Exception as e:
                st.error(f"Connection failed: {e}")
                st.session_state.sql_result = None

    # Display result
    if st.session_state.sql_result:
        data = st.session_state.sql_result
        if "rows" in data:
            df = pd.DataFrame(data["rows"])

            st.subheader("Generated SQL")
            st.code(data.get("sql", ""), language="sql")

            st.subheader("Results Table")
            st.dataframe(df, use_container_width=True)

            if not df.empty:
                st.download_button(
                    "📤 Export CSV",
                    df.to_csv(index=False).encode('utf-8'),
                    "result.csv",
                    "text/csv",
                    use_container_width=True
                )

            st.subheader("Chart")
            if not df.empty:
                num_cols = df.select_dtypes(include="number").columns.tolist()
                cat_cols = df.select_dtypes(exclude="number").columns.tolist()

                # Pie
                if chart_type == "Pie" and num_cols and cat_cols:
                    grouped = df[[cat_cols[0], num_cols[0]]].dropna().groupby(cat_cols[0], as_index=False)[num_cols[0]].sum()
                    if not grouped.empty:
                        fig, ax = plt.subplots()
                        ax.pie(grouped[num_cols[0]], labels=grouped[cat_cols[0]], autopct='%1.1f%%')
                        ax.set_title(f"{num_cols[0]} by {cat_cols[0]}")
                        st.pyplot(fig)
                        plt.close(fig)
                    else:
                        st.warning("Not enough data for pie chart.")

                # Bar
                elif chart_type == "Bar" and num_cols and cat_cols:
                    st.bar_chart(df.set_index(cat_cols[0])[num_cols[0]])

                # Line
                elif chart_type == "Line" and num_cols:
                    st.line_chart(df[num_cols])

                # Area
                elif chart_type == "Area" and num_cols:
                    st.area_chart(df[num_cols])

                # Auto fallback
                else:
                    if num_cols and cat_cols:
                        st.bar_chart(df.set_index(cat_cols[0])[num_cols[0]])

            st.write(f"**Rows returned:** {len(df)}")

else:
    # Normal chat interface for all other modes
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            display_message(msg)

    col_text, col_voice = st.columns([4, 1])
    query = None
    with col_text:
        text_query = st.chat_input("Ask something...")
    with col_voice:
        if st.button("🎤 Voice"):
            try:
                ap = record_audio(10)
                query = transcribe_audio(ap)
                st.success(f"**You said:** {query}")
            except Exception as e:
                st.error(f"Voice error: {e}")

    if text_query:
        query = text_query

    if query:
        user_msg = {"role": "user", "content": query}
        st.session_state.messages.append(user_msg)
        with st.chat_message("user"):
            st.markdown(query)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                answer_summary = "(no response)"
                rich_type = None
                rich_data = None

                try:
                    if mode == "General":
                        messages_for_grok = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                        payload = {"messages": messages_for_grok}
                        r = requests.post(f"{GENERAL_BACKEND}/chat", json=payload, timeout=120)
                        r.raise_for_status()
                        answer_summary = r.json().get("response", "No response")

                    elif mode == "Documents (PDFs)":
                        r = requests.post(f"{RAG_PDF_BACKEND}/chat", json={"query": query}, timeout=240)
                        r.raise_for_status()
                        answer_summary = r.json().get("response", "No answer")

                    elif mode == "Transcribed Audio":
                        r = requests.post(f"{AUDIO_RAG_BACKEND}/query", json={"question": query}, timeout=180)
                        r.raise_for_status()
                        answer_summary = r.json().get("answer", "No relevant info")

                    elif mode == "Transcribed Video":
                        if not st.session_state.video_transcript:
                            answer_summary = "Please transcribe a video first in the sidebar."
                        else:
                            payload = {"question": query, "context": st.session_state.video_transcript}
                            r = requests.post(f"{VIDEO_BACKEND}/query", json=payload, timeout=300)
                            r.raise_for_status()
                            answer_summary = r.json().get("answer", "No info found")

                    elif mode == "Images":
                        payload = {
                            "session_id": st.session_state.image_session_id,
                            "message": query
                        }
                        r = requests.post(f"{IMAGE_BACKEND}/chat", json=payload, timeout=240)
                        r.raise_for_status()
                        answer_summary = r.json().get("response", "No info")

                except Exception as e:
                    answer_summary = f"Error: {str(e)}"

            current_msg = {"content": answer_summary, "rich_type": rich_type, "rich_data": rich_data}
            display_message(current_msg)

            if st.session_state.last_spoken != answer_summary:
                speak_response(answer_summary)
                st.session_state.last_spoken = answer_summary

        st.session_state.messages.append({
            "role": "assistant",
            "content": answer_summary,
            "rich_type": rich_type,
            "rich_data": rich_data
        })

st.caption("Default: General chat | Check the box to enable specialized RAG modes • Voice input supported")