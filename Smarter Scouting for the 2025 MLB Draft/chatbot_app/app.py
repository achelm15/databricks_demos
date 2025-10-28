import streamlit as st
import requests
import os

# ---- Config ----
ENDPOINT_URL = "DATABRICKS_HOST/serving-endpoints/agents_alexander_booth-rag_demo-scouting_reports_agent/invocations"
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN") 

# ---- Streamlit Setup ----
st.set_page_config(page_title="Scouting Report RAG", layout="wide")
st.title("🧢 Scouting Report Chat Assistant")

# Sidebar: Reset chat
st.sidebar.header("🧠 Session Control")
if st.sidebar.button("Start New Chat / Player"):
    st.session_state.messages = []
    st.rerun()

# Session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display previous messages
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input box
user_input = st.chat_input("Ask about a player...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    # Build request payload
    payload = {
        "query": user_input,
        "messages": st.session_state.messages[:-1]
    }

    # Send request to the model serving endpoint
    headers = {
        "Authorization": f"Bearer {DATABRICKS_TOKEN}",
        "Content-Type": "application/json"
    }

    with st.spinner("Thinking..."):
        response = requests.post(ENDPOINT_URL, headers=headers, json={"inputs": payload})

    if response.status_code == 200:
        answer = response.json().get("predictions", ["(No answer returned)"])[0]
    else:
        answer = f"❌ Error {response.status_code}: {response.text}"

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.chat_message("assistant").write(answer)
