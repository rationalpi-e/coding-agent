import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agent.graph import run_agent_stream

st.set_page_config(page_title="Coding Agent", layout="wide")
st.title("Coding Agent")
st.caption("Supports Python · C++ · SQL")

if "messages" not in st.session_state:
    st.session_state.messages = []

st.sidebar.markdown("### Settings")
model = st.sidebar.selectbox(
    "LLM Model",
    ["groq", "gemini", "claude", "openai"],
    index=0,
    format_func=lambda x: {
        "groq": "⚡ Groq — Llama 3.3 70B (free)",
        "gemini": "🔵 Google — Gemini 2.0 Flash (free)",
        "claude": "🟠 Anthropic — Claude Haiku",
        "openai": "🟢 OpenAI — GPT-4o Mini"
    }[x]
)

language = st.sidebar.selectbox("Default Language", ["Python", "C++", "SQL"])

st.sidebar.markdown("---")
st.sidebar.markdown("### Upload a File")
uploaded_file = st.sidebar.file_uploader(
    "Upload code file to analyze",
    type=["py", "cpp", "sql", "js", "txt", "json", "csv"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("**Skills available:**")
st.sidebar.markdown("🔨 Code execution + TDD\n\n🔍 Code review\n\n📄 File analysis\n\n💬 General Q&A")
st.sidebar.caption("💡 Skill is auto-detected from your message.")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Write code, review my code, analyze this file..."):
    file_content = ""
    file_name = ""

    if uploaded_file:
        file_content = uploaded_file.read().decode("utf-8")
        file_name = uploaded_file.name
        st.sidebar.success(f"✅ {file_name} loaded")

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
        if file_name:
            st.caption(f"📄 File attached: {file_name}")

    with st.chat_message("assistant"):
        response = st.write_stream(run_agent_stream(
            prompt,
            language=language,
            model_name=model,
            uploaded_file_content=file_content,
            uploaded_file_name=file_name
        ))

    st.session_state.messages.append({"role": "assistant", "content": response})