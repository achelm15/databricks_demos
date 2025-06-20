import streamlit as st
import os
import requests

# Environment config
SERVING_ENDPOINT = os.environ["MODEL_SERVING_ENDPOINT"]
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "https://e2-demo-field-eng.cloud.databricks.com")
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]

# Page config
st.set_page_config(page_title="Scouting Report Chat", page_icon="🔎", layout="wide")
st.title("🔎 Scouting Report Chat")
st.caption("This demo lets you chat with a RAG-powered assistant trained on baseball scouting reports. Answers are based only on indexed reports, and source references are included below each response.")

with st.expander("💡 Example questions", expanded=True):
    examples = [
        "Tell me about Roman Anthony.",
        "What are Andrew Painter’s strengths?",
        "Compare Marcelo Mayer to Jordan Lawlar."
    ]
    for example in examples:
        if st.button(example):
            st.session_state.history.append({"role": "user", "content": example})
            st.rerun()

# Clear button
if st.button("🧹 Clear chat"):
    st.session_state.history = []
    st.rerun()

# Session state for chat history
if "history" not in st.session_state:
    st.session_state.history = []

# Input box
user_input = st.chat_input("Ask about a player...")

# When the user submits a new message
if user_input:
    st.session_state.history.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
        try:
            # Format history for endpoint
            messages = [
                {"role": "user", "content": m["content"]} if m["role"] == "user"
                else {"role": "assistant", "content": m["content"]}
                for m in st.session_state.history
            ]

            payload = {
                "query": user_input,
                "messages": messages
            }

            response = requests.post(
                f"{DATABRICKS_HOST}/serving-endpoints/{SERVING_ENDPOINT}/invocations",
                headers={
                    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
                    "Content-Type": "application/json"
                },
                json={"inputs": payload},
                timeout=30
            )

            response.raise_for_status()
            reply = response.json().get("predictions", ["(No answer returned)"])[0]
        except Exception as e:
            reply = f"ERROR: {e}"

        st.session_state.history.append({"role": "assistant", "content": reply})

# Render full chat history
for entry in st.session_state.history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
