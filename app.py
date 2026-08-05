"""Streamlit chat interface for the Hybrid RAG API."""

import re

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000/ask"
REQUEST_TIMEOUT_SECONDS = 90


def initialize_chat() -> None:
    """Create the conversation store once per browser session."""
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []


def render_sources(citations: list[dict]) -> None:
    """Render response citations in a clearly separate section."""
    if not citations:
        return

    st.markdown("#### Sources")
    for citation in citations:
        source = citation.get("source", "Unknown document")
        page = citation.get("page", "Unknown")
        st.markdown(f"📄 **{source}** (Page {page})")


def format_answer(answer: str) -> str:
    """Normalize LLM output so Markdown renders correctly."""

    if not answer:
        return ""

    # Normalize line endings
    answer = answer.replace("\r\n", "\n").replace("\r", "\n")

    # Put every bullet on its own line
    answer = re.sub(r"\s*•\s*", "\n• ", answer)

    # Put headings on a new line
    answer = re.sub(r"\s*(#{1,6}\s)", r"\n\n\1", answer)

    # Remove excessive blank lines
    answer = re.sub(r"\n{3,}", "\n\n", answer)

    return answer.strip()


def render_assistant_message(message: dict) -> None:
    """Render an assistant answer with its verification state and sources."""
    with st.chat_message("assistant", avatar="🤖"):
        if message["verified"]:
            st.success("✅ Verified Answer")
        else:
            st.warning("⚠ Answer may be incomplete")

        # st.markdown preserves headings, lists, tables, and other Markdown.
        st.markdown(format_answer(message["content"]))
        render_sources(message.get("citations", []))


def render_history() -> None:
    """Render the complete conversation in chronological order."""
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            with st.chat_message("user", avatar="👤"):
                st.markdown(message["content"])
        else:
            render_assistant_message(message)


def ask_api(question: str) -> dict | None:
    """Send a question to FastAPI and return a validated response payload."""
    try:
        with st.spinner("Searching your documents and preparing an answer..."):
            response = requests.post(
                API_URL,
                json={"question": question},
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
    except requests.RequestException:
        st.error("Unable to connect to FastAPI.")
        return None

    try:
        payload = response.json()
    except ValueError:
        payload = {}

    # Normalize bullet formatting for Markdown rendering
    if "answer" in payload:
        payload["answer"] = re.sub(
            r"^\s*•\s*",
            "- ",
            payload["answer"],
            flags=re.MULTILINE,
        )
    if response.status_code == 429:
        st.warning("⚠ Groq Rate Limit Reached")
        st.info(str(payload.get("detail", response.text)))
        return None

    if response.status_code == 500:
        st.error("❌ Internal Server Error")
        return None

    if not response.ok:
        st.error(str(payload.get("detail", response.text)))
        return None

    return payload


st.set_page_config(
    page_title="Hybrid RAG Assistant",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
        .block-container {
            max-width: 1080px;
            padding-top: 2.5rem;
            padding-bottom: 2rem;
        }
        .rag-title {
            font-size: clamp(2rem, 5vw, 3rem);
            font-weight: 700;
            letter-spacing: -0.04em;
            margin-bottom: 0.25rem;
        }
        .rag-subtitle {
            color: #64748b;
            font-size: 1rem;
            margin-bottom: 1.5rem;
        }
        div[data-testid="stChatMessage"] {
            border: 1px solid rgba(148, 163, 184, 0.22);
            border-radius: 18px;
            margin-bottom: 0.9rem;
            padding: 0.2rem 0.75rem;
            box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
        }
        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background: rgba(37, 99, 235, 0.08);
            flex-direction: row-reverse;
            text-align: right;
        }
        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background: rgba(248, 250, 252, 0.9);
        }
        div[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) .stMarkdown {
            text-align: left;
        }
        div.stButton > button {
            border-radius: 10px;
            font-weight: 600;
            min-height: 2.6rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

initialize_chat()

header_column, clear_column = st.columns([6, 1], vertical_alignment="bottom")
with header_column:
    st.markdown(
        '<div class="rag-title">Hybrid RAG Assistant</div>', unsafe_allow_html=True
    )
    st.markdown(
        '<div class="rag-subtitle">Ask questions about your indexed documents.</div>',
        unsafe_allow_html=True,
    )
with clear_column:
    if st.button("Clear Chat", use_container_width=True):
        st.session_state.chat_history = []
        st.rerun()

st.divider()
render_history()

with st.form("ask_form", clear_on_submit=True):
    question = st.text_area(
        "Ask a question",
        placeholder="e.g. What is Casual Leave?",
        height=90,
        label_visibility="collapsed",
    )
    ask_clicked = st.form_submit_button("Ask", use_container_width=True)

if ask_clicked:
    question = question.strip()
    if not question:
        st.warning("Please enter a question.")
        st.stop()

    st.session_state.chat_history.append({"role": "user", "content": question})
    payload = ask_api(question)

    if payload is not None:
        st.session_state.chat_history.append(
            {
                "role": "assistant",
                "content": payload.get("answer", ""),
                "verified": bool(payload.get("verified", False)),
                "citations": payload.get("citations", []),
            }
        )

    st.rerun()
