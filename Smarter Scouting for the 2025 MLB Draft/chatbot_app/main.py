import streamlit as st
import os
import requests

# Environment config
SERVING_ENDPOINT = os.environ["MODEL_SERVING_ENDPOINT"]
DATABRICKS_HOST = os.environ["DATABRICKS_HOST"]
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]

# Page config
st.set_page_config(page_title="Scouting Report Chat", page_icon="🔎", layout="wide")
st.title("🔎 Scouting Report Chat")
st.caption("Chat with a RAG-powered assistant trained on baseball scouting reports. Answers are based only on indexed reports, and source references are included below each response.")

with st.expander("💡 Example questions", expanded=True):
    st.markdown("""
    💬 **Try asking:**
    - `Tell me about Jace Laviolette.`
    - `What are Jamie Arnold’s strengths?`
    - `Compare Ethan Holliday to Billy Carlson.`
    """)

# Clear chat button
if st.button("🧹 Clear chat"):
    st.session_state.history = []
    st.rerun()

# Session state
if "history" not in st.session_state:
    st.session_state.history = []

# Input
user_input = st.chat_input("Ask about a player...")

if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
        try:
            # Build payload for the endpoint’s enforced schema
            payload = {
                "inputs": {
                "request_id": f"app-{len(st.session_state.history)+1}",
                "source": "streamlit",
                "text_assessments": user_input,
                "retrieval_assessments": ""  # optional context
                }
            }

            response = requests.post(
                f"https://{DATABRICKS_HOST}/serving-endpoints/{SERVING_ENDPOINT}/invocations",
                headers={
                    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=60,
            )
            response.raise_for_status()

            body = response.json()
            reply = (
                body.get("choices", [{}])[0].get("message", {}).get("content")
                or (body.get("outputs", [{}])[0].get("content") if body.get("outputs") else None)
                or (body.get("predictions", [None])[0] if body.get("predictions") else None)
                or str(body)
            )

        except Exception as e:
            reply = f"ERROR: {e}"

        st.session_state.history.append({"role": "assistant", "content": reply})

# Render chat
for entry in st.session_state.history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
