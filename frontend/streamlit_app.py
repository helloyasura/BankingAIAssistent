import json

import httpx
import streamlit as st

API = "http://localhost:8000/api/v1"
USERS = {
    "viewer@combank.com": "viewer",
    "analyst@commercialbank.com": "analyst123",
    "admin@commercialbank.com": "admin123",
}

st.set_page_config(page_title="Commercial Bank AI", layout="wide")
st.title("Commercial Bank — Enterprise AI Assistant")

if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "activities" not in st.session_state:
    st.session_state.activities = []

with st.sidebar:
    email = st.selectbox("User", list(USERS.keys()))
    password = USERS[email]
    if st.button("Login"):
        r = httpx.post(f"{API}/auth/login", json={"email": email, "password": password})
        if r.status_code == 200:
            st.session_state.user = r.json()
            st.success(f"Logged in as {st.session_state.user['display_name']}")
        else:
            st.error("Login failed")

chat_col, activity_col = st.columns([2, 1])

with chat_col:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

with activity_col:
    st.subheader("Agent Activity")
    if st.session_state.activities:
        for activity in st.session_state.activities:
            st.markdown(f"**{activity['node']}** — {activity['status']}")
            st.caption(activity["detail"])
    else:
        st.caption("Activities appear here as the agent runs.")

if prompt := st.chat_input("Ask a question..."):
    if not st.session_state.user:
        st.warning("Login first")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.session_state.activities = []
        headers = {"Authorization": f"Bearer {st.session_state.user['access_token']}"}
        answer = "Error: no response"

        with httpx.Client(timeout=120) as client:
            try:
                with client.stream(
                    "POST",
                    f"{API}/chat/stream",
                    headers=headers,
                    json={"message": prompt},
                ) as resp:
                    if resp.status_code != 200:
                        answer = f"Error: {resp.status_code}"
                    else:
                        for line in resp.iter_lines():
                            if not line.startswith("data: "):
                                continue
                            event = json.loads(line[6:])
                            if event["type"] == "activity":
                                st.session_state.activities.append(event["activity"])
                            elif event["type"] == "answer":
                                answer = event["content"]
                            elif event["type"] == "error":
                                answer = event["content"]
            except httpx.RemoteProtocolError:
                if answer == "Error: no response":
                    answer = "Connection closed before the response completed. Try again."

        st.session_state.messages.append({"role": "assistant", "content": answer})
        st.rerun()
