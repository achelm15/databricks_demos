import streamlit as st
import os
import requests

# Environment config
SERVING_ENDPOINT = os.environ["MODEL_SERVING_ENDPOINT"]
DATABRICKS_HOST = os.environ.get("DATABRICKS_HOST", "DATABRICKS_HOST")
DATABRICKS_TOKEN = os.environ["DATABRICKS_TOKEN"]

# Page config
st.set_page_config(page_title="Scouting Report Chat", page_icon="🔎", layout="wide")
st.title("🔎 Scouting Report Chat")
st.caption("This demo lets you chat with a RAG-powered assistant trained on baseball scouting reports. Answers are based only on indexed reports, and source references are included below each response.")

# Example questions (static markdown)
with st.expander("💡 Example questions", expanded=True):
    st.markdown("""
    💬 **Try asking:**
    - `Tell me about Jace LaViolette.`
    - `What are Jamie Arnold’s strengths?`
    - `Compare Ethan Holliday to Billy Carlson.`
    """)

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
                {"role": m["role"], "content": m["content"]}
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
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            reply = response.json()["choices"][0]["message"]["content"]
        except Exception as e:
            reply = f"ERROR: {e}"

        st.session_state.history.append({"role": "assistant", "content": reply})

# Render full chat history
for entry in st.session_state.history:
    with st.chat_message(entry["role"]):
        st.markdown(entry["content"])
