import json
import os
import uuid

import httpx
import streamlit as st

API = os.environ.get("API_BASE_URL", "http://localhost:8000/api/v1")
BACKEND_UNAVAILABLE_MSG = (
    "Backend unavailable. Start API: uv run uvicorn asgi:app --reload --port 8000"
)
USERS = {
    "analyst@commercialbank.com": "analyst123",
    "admin@commercialbank.com": "admin123",
    "viewer@combank.com": "viewer",
}

st.set_page_config(page_title="Commercial Bank AI", layout="wide")
st.title("Commercial Bank — Enterprise AI Assistant")


def _headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {st.session_state.user['access_token']}"}


def _submit_feedback(message_id: str, rating: int, comment: str | None = None) -> bool | None:
    payload = {
        "session_id": st.session_state.session_id,
        "rating": rating,
        "message_id": message_id,
    }
    if comment:
        payload["comment"] = comment
    try:
        r = httpx.post(f"{API}/chat/feedback", headers=_headers(), json=payload, timeout=30)
        return r.status_code == 200
    except (httpx.ConnectError, httpx.RequestError):
        st.error(BACKEND_UNAVAILABLE_MSG)
        return None


def _approval_action(session_id: str, approved: bool) -> dict | None:
    try:
        r = httpx.post(
            f"{API}/chat/approvals/{session_id}",
            headers=_headers(),
            json={"approved": approved},
            timeout=30,
        )
        return r.json() if r.status_code == 200 else {"status": "error"}
    except (httpx.ConnectError, httpx.RequestError):
        st.error(BACKEND_UNAVAILABLE_MSG)
        return None


def _stream_chat(message: str, *, approved: bool = False) -> tuple[str, bool, list[dict]]:
    answer = "Error: no response"
    awaiting_approval = False
    activities: list[dict] = []
    payload = {
        "message": message,
        "session_id": st.session_state.session_id,
        "approved": approved,
    }

    with httpx.Client(timeout=120) as client:
        try:
            with client.stream(
                "POST",
                f"{API}/chat/stream",
                headers=_headers(),
                json=payload,
            ) as resp:
                if resp.status_code != 200:
                    return f"Error: {resp.status_code}", False, activities
                for line in resp.iter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    if event["type"] == "activity":
                        activities.append(event["activity"])
                    elif event["type"] == "answer":
                        answer = event["content"]
                        awaiting_approval = event.get("awaiting_approval", False)
                        if event.get("session_id"):
                            st.session_state.session_id = event["session_id"]
                    elif event["type"] == "error":
                        answer = event["content"]
        except httpx.RemoteProtocolError:
            if answer == "Error: no response":
                answer = "Connection closed before the response completed. Try again."
        except (httpx.ConnectError, httpx.RequestError):
            st.error(BACKEND_UNAVAILABLE_MSG)
            answer = BACKEND_UNAVAILABLE_MSG

    return answer, awaiting_approval, activities


if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "activities" not in st.session_state:
    st.session_state.activities = []
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())

with st.sidebar:
    email = st.selectbox("User", list(USERS.keys()))
    password = USERS[email]
    if st.button("Login"):
        try:
            r = httpx.post(f"{API}/auth/login", json={"email": email, "password": password})
            if r.status_code == 200:
                st.session_state.user = r.json()
                st.success(f"Logged in as {st.session_state.user['display_name']}")
            else:
                st.error("Login failed")
        except (httpx.ConnectError, httpx.RequestError):
            st.error(BACKEND_UNAVAILABLE_MSG)

    if st.session_state.user:
        st.caption(f"Session: `{st.session_state.session_id[:8]}…`")
        if st.button("New session"):
            st.session_state.session_id = str(uuid.uuid4())
            st.session_state.messages = []
            st.session_state.activities = []
            st.rerun()

chat_col, activity_col = st.columns([2, 1])

with chat_col:
    for idx, msg in enumerate(st.session_state.messages):
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

            if msg["role"] != "assistant" or not st.session_state.user:
                continue

            if msg.get("awaiting_approval"):
                st.warning("Human approval required before this action runs.")
                a1, a2 = st.columns(2)
                if a1.button("Approve", key=f"approve_{idx}"):
                    result = _approval_action(st.session_state.session_id, approved=True)
                    if result is None:
                        pass
                    elif result.get("status") == "approved":
                        source = msg.get("source_message", "")
                        answer, awaiting, activities = _stream_chat(source, approved=True)
                        st.session_state.activities = activities
                        st.session_state.messages[idx] = {
                            **msg,
                            "content": answer,
                            "awaiting_approval": awaiting,
                            "source_message": source if awaiting else None,
                        }
                        st.rerun()
                    else:
                        st.error("No pending approval found. Try your question again.")
                if a2.button("Reject", key=f"reject_{idx}"):
                    _approval_action(st.session_state.session_id, approved=False)
                    st.session_state.messages[idx] = {
                        **msg,
                        "content": "Action rejected. The sensitive operation was not executed.",
                        "awaiting_approval": False,
                        "source_message": None,
                    }
                    st.rerun()
                continue

            if msg.get("feedback"):
                st.caption(f"Thanks for your feedback ({msg['feedback']}).")
                continue

            f1, f2 = st.columns(2)
            if f1.button("👍 Helpful", key=f"up_{idx}"):
                ok = _submit_feedback(msg["id"], rating=1)
                if ok is True:
                    st.session_state.messages[idx]["feedback"] = "helpful"
                    st.rerun()
                elif ok is False:
                    st.error("Could not save feedback.")
            if f2.button("👎 Not helpful", key=f"down_{idx}"):
                st.session_state.messages[idx]["pending_downvote"] = True
                st.rerun()

            if msg.get("pending_downvote"):
                comment = st.text_input(
                    "Optional comment",
                    key=f"comment_{idx}",
                    placeholder="What was wrong with this answer?",
                )
                if st.button("Submit feedback", key=f"submit_down_{idx}"):
                    ok = _submit_feedback(msg["id"], rating=-1, comment=comment or None)
                    if ok is True:
                        st.session_state.messages[idx]["feedback"] = "not helpful"
                        st.session_state.messages[idx].pop("pending_downvote", None)
                        st.rerun()
                    elif ok is False:
                        st.error("Could not save feedback.")

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
        answer, awaiting_approval, activities = _stream_chat(prompt)
        st.session_state.activities = activities
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "id": str(uuid.uuid4()),
                "awaiting_approval": awaiting_approval,
                "source_message": prompt if awaiting_approval else None,
            }
        )
        st.rerun()
