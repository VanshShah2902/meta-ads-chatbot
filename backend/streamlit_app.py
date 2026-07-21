import os
import sys
from pathlib import Path

app_dir = Path(__file__).parent.resolve()
os.chdir(app_dir)
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

import streamlit as st
import threading
import time
from datetime import datetime, timedelta

try:
    for key, value in st.secrets.items():
        if isinstance(value, str):
            os.environ.setdefault(key, value)
except Exception:
    pass

from config import GOOGLE_DRIVE_FOLDER_ID
from database import init_db, get_stats, get_schema_description
from query_engine import ask
from drive_sync import sync_from_drive

st.set_page_config(
    page_title="Meta Ads Chatbot",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0c29 0%, #1a1040 40%, #0d1b2a 100%);
    color: #e0e0e0;
    font-family: 'Inter', sans-serif;
}
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] {
    background: rgba(15, 12, 41, 0.95);
    border-right: 1px solid rgba(255,255,255,0.08);
}

.main-title {
    text-align: center;
    padding: 1.5rem 0 0.5rem;
}
.main-title h1 {
    background: linear-gradient(135deg, #7c3aed, #06b6d4, #ec4899);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 2.2rem;
    font-weight: 700;
    margin: 0;
}
.main-title p {
    color: #94a3b8;
    font-size: 0.9rem;
    margin: 0.3rem 0 0;
}

.stats-bar {
    display: flex;
    justify-content: center;
    gap: 2rem;
    padding: 0.8rem;
    margin: 0.5rem auto 1rem;
    max-width: 700px;
    background: rgba(255,255,255,0.04);
    border-radius: 12px;
    border: 1px solid rgba(255,255,255,0.06);
}
.stat-item {
    text-align: center;
}
.stat-value {
    font-size: 1.3rem;
    font-weight: 700;
    color: #7c3aed;
}
.stat-label {
    font-size: 0.7rem;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

.chat-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 0 1rem;
}

.user-msg {
    background: linear-gradient(135deg, #7c3aed, #6d28d9);
    color: white;
    padding: 0.8rem 1.2rem;
    border-radius: 18px 18px 4px 18px;
    margin: 0.5rem 0;
    max-width: 80%;
    margin-left: auto;
    font-size: 0.95rem;
}
.bot-msg {
    background: rgba(255,255,255,0.06);
    border: 1px solid rgba(255,255,255,0.08);
    color: #e2e8f0;
    padding: 0.8rem 1.2rem;
    border-radius: 18px 18px 18px 4px;
    margin: 0.5rem 0;
    max-width: 85%;
    font-size: 0.95rem;
    backdrop-filter: blur(10px);
}
.bot-msg strong { color: #7c3aed; }

.sql-box {
    background: rgba(0,0,0,0.3);
    border: 1px solid rgba(124,58,237,0.3);
    border-radius: 8px;
    padding: 0.6rem;
    margin-top: 0.5rem;
    font-family: 'Fira Code', monospace;
    font-size: 0.78rem;
    color: #a78bfa;
    overflow-x: auto;
}

.suggestion-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.5rem;
    justify-content: center;
    margin: 1rem auto;
    max-width: 700px;
}

div[data-testid="stChatInput"] textarea {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    color: #e2e8f0 !important;
    border-radius: 12px !important;
}
div[data-testid="stChatInput"] textarea:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 15px rgba(124,58,237,0.2) !important;
}

div[data-testid="stChatInput"] button {
    background: linear-gradient(135deg, #7c3aed, #6d28d9) !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
}

[data-testid="stDataFrame"] {
    background: rgba(255,255,255,0.03);
    border-radius: 8px;
}

.sync-status {
    text-align: center;
    padding: 0.3rem;
    font-size: 0.75rem;
    color: #64748b;
}
.sync-status .success { color: #22c55e; }
.sync-status .running { color: #f59e0b; }

div[data-testid="stExpander"] {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 8px;
}

button[kind="secondary"] {
    background: rgba(124,58,237,0.15) !important;
    border: 1px solid rgba(124,58,237,0.3) !important;
    color: #c4b5fd !important;
    border-radius: 20px !important;
}
button[kind="secondary"]:hover {
    background: rgba(124,58,237,0.25) !important;
    border-color: #7c3aed !important;
}
</style>
"""

st.markdown(DARK_CSS, unsafe_allow_html=True)


@st.cache_resource
def setup_db():
    init_db()
    return True


@st.cache_data(ttl=60)
def cached_stats():
    return get_stats()


def auto_sync_if_needed():
    if "sync_checked" in st.session_state:
        return
    st.session_state.sync_checked = True

    if not GOOGLE_DRIVE_FOLDER_ID:
        return

    run_sync()


def run_sync():
    if st.session_state.get("sync_running"):
        return
    st.session_state.sync_running = True

    def _sync():
        try:
            result = sync_from_drive()
            st.session_state.sync_result = result
            st.session_state.sync_time = datetime.now().strftime("%H:%M:%S")
        except Exception as e:
            st.session_state.sync_result = {"status": "error", "message": str(e)}
        finally:
            st.session_state.sync_running = False

    thread = threading.Thread(target=_sync, daemon=True)
    thread.start()


setup_db()

if "messages" not in st.session_state:
    st.session_state.messages = []

auto_sync_if_needed()

stats = cached_stats()

st.markdown("""
<div class="main-title">
    <h1>📊 Meta Ads Chatbot</h1>
    <p>Ask anything about your Meta Ads campaigns</p>
</div>
""", unsafe_allow_html=True)

if stats["total_rows"] > 0:
    date_range = ""
    if stats.get("date_range_start") and stats.get("date_range_end"):
        date_range = f"{stats['date_range_start']} to {stats['date_range_end']}"
    st.markdown(f"""
    <div class="stats-bar">
        <div class="stat-item"><div class="stat-value">{stats['total_rows']:,}</div><div class="stat-label">Rows</div></div>
        <div class="stat-item"><div class="stat-value">{stats['total_campaigns']}</div><div class="stat-label">Campaigns</div></div>
        <div class="stat-item"><div class="stat-value">{stats['total_adsets']}</div><div class="stat-label">Ad Sets</div></div>
        <div class="stat-item"><div class="stat-value">{stats['total_ads']}</div><div class="stat-label">Ads</div></div>
        <div class="stat-item"><div class="stat-value">{stats['files_imported']}</div><div class="stat-label">Files</div></div>
    </div>
    """, unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### ⚙️ Settings")

    st.markdown("---")
    st.markdown("### 🔄 Google Drive Sync")

    if st.session_state.get("sync_running"):
        st.info("⏳ Sync in progress...")
    elif st.session_state.get("sync_result"):
        result = st.session_state.sync_result
        if isinstance(result, dict) and "imported" in result:
            imported = len(result.get("imported", []))
            skipped = len(result.get("skipped", []))
            errors = len(result.get("errors", []))
            st.success(f"✅ Last sync: {imported} imported, {skipped} skipped, {errors} errors")
            if result.get("errors"):
                for e in result["errors"]:
                    st.error(f"❌ {e['filename']}: {e['error']}")
        elif isinstance(result, dict) and result.get("status") == "error":
            st.error(f"❌ {result.get('message', 'Sync failed')}")

    if st.button("🔄 Sync Now", use_container_width=True, disabled=st.session_state.get("sync_running", False)):
        run_sync()
        st.rerun()

    st.markdown("---")
    st.markdown("### 📋 Quick Reference")
    st.markdown("""
    **Abbreviations:**
    - **CPT** = Cost Per Transaction
    - **CPC** = Cost Per Click
    - **CTR** = Click-Through Rate
    - **CVR** = Conversion Rate
    - **C2V** = Click to View Ratio
    - **ROAS** = Return On Ad Spend
    - **CPM** = Cost Per 1000 Impressions
    - **AOV** = Average Order Value
    """)

    if date_range if stats["total_rows"] > 0 else False:
        st.markdown(f"**Date range:** {date_range}")

SUGGESTIONS = [
    "What was the total spend last month?",
    "Top 5 campaigns by ROAS",
    "What is the CPT for each campaign?",
    "CVR by platform",
    "Daily spend trend for June",
]

def process_question(question: str):
    st.session_state.messages.append({"role": "user", "content": question})
    st.session_state.pending_question = question


if not st.session_state.messages:
    cols = st.columns(len(SUGGESTIONS))
    for i, suggestion in enumerate(SUGGESTIONS):
        with cols[i]:
            if st.button(suggestion, key=f"sug_{i}", use_container_width=True):
                process_question(suggestion)
                st.rerun()

for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="user-msg">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        answer = msg["content"]
        answer_html = answer.replace("**", "<strong>", 1)
        while "**" in answer_html:
            answer_html = answer_html.replace("**", "</strong>", 1)
            if "**" in answer_html:
                answer_html = answer_html.replace("**", "<strong>", 1)
        st.markdown(f'<div class="bot-msg">{answer_html}</div>', unsafe_allow_html=True)

        if msg.get("sql"):
            with st.expander("🔍 View SQL"):
                st.code(msg["sql"], language="sql")

        if msg.get("data") and len(msg["data"]) > 1:
            with st.expander(f"📊 View Data ({len(msg['data'])} rows)"):
                st.dataframe(msg["data"], use_container_width=True)

pending = st.session_state.pop("pending_question", None)
if pending:
    with st.spinner("Analyzing your data..."):
        history = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages[:-1]]
        result = ask(pending, history)

    bot_msg = {
        "role": "assistant",
        "content": result["answer"],
        "sql": result.get("sql"),
        "data": result.get("data"),
    }
    st.session_state.messages.append(bot_msg)
    st.rerun()

if prompt := st.chat_input("Ask about your Meta Ads data..."):
    process_question(prompt)
    st.rerun()
