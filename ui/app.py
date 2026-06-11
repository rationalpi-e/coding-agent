import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from agent.graph import run_agent

st.set_page_config(page_title="Coding Agent", layout="wide")
st.title("Coding Agent")
st.caption("Supports Python · C++ · SQL")

if "messages" not in st.session_state:
    st.session_state.messages = []

language = st.sidebar.selectbox("Language", ["Python", "C++", "SQL"])
st.sidebar.markdown("---")
st.sidebar.markdown("**How it works**")
st.sidebar.markdown("1. Writes a failing test\n2. Writes code\n3. Runs & fixes until passing")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Describe what you want to build..."):
    full_prompt = f"Language: {language}\n\nTask: {prompt}"
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Agent thinking..."):
            response = run_agent(full_prompt)
        st.markdown(response)

    st.session_state.messages.append({"role": "assistant", "content": response})
