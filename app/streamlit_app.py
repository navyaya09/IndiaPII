import html
from collections import Counter

import requests
import pandas as pd
import streamlit as st

# =========================================================
# CONFIG
# =========================================================

API = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="IndiaPII | Privacy Intelligence",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

COLORS = {
    "PERSON": ("#DBEAFE", "#1D4ED8"),
    "ADDRESS": ("#F3E8FF", "#7E22CE"),
    "PHONE": ("#DCFCE7", "#15803D"),
    "AADHAAR": ("#FEF3C7", "#B45309"),
    "PAN": ("#FCE7F3", "#BE185D"),
    "EMAIL": ("#E0F2FE", "#0369A1"),
    "UPI": ("#FFE4E6", "#BE123C")
}

SAMPLES = {
    "English": (
        "My name is Rahul Sharma. My email is rahul@example.com "
        "and my phone number is 9876543210."
    ),
    "Hindi": (
        "मेरा नाम अमित शर्मा है और मेरा मोबाइल नंबर 9876543210 है।"
    ),
    "Hinglish": (
        "Mera naam Rahul Sharma hai aur mera email "
        "rahul@example.com hai."
    )
}

for key, value in {
    "input_text": "",
    "entities": [],
    "original": "",
    "masked": "",
    "mapping": {},
    "restored": "",
    "active_page": "Detect",
    "navigation_page": "Detect",
    "language": "English",
    "genai_input": "",
    "genai_response": "",
    "genai_masked": "",
    "genai_task": "Summarize",
    "rag_document_id": "",
    "rag_document_name": "",
    "rag_masked_text": "",
    "rag_chat_history": []
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


def navigate_to(page):
    """Change the sidebar page before Streamlit rebuilds its widgets."""
    st.session_state.navigation_page = page


# =========================================================
# CUSTOM UI
# =========================================================

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

.stApp {
    background: #F4F7FC;
}

.block-container {
    max-width: 1350px;
    padding-top: 1.5rem;
    padding-bottom: 3rem;
}

[data-testid="stSidebar"] {
    background: #111C32;
}

/* Sidebar navigation */
[data-testid="stSidebar"] {
    background: #111C32;
}

[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span {
    color: #E5EDF8;
}

/* Selectbox readability */
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #172B4D !important;
}

/* Sidebar information cards */
[data-testid="stSidebar"] [data-testid="stAlert"] p {
    color: #172B4D !important;
}

/* Sidebar radio labels */
[data-testid="stSidebar"] [role="radiogroup"] label {
    color: #E5EDF8 !important;
}

.hero {
    background: linear-gradient(120deg,#111C32,#234D79);
    padding: 30px;
    border-radius: 20px;
    color: white;
    margin-bottom: 22px;
}

.hero h1 {
    color: white;
    font-size: 38px;
    font-weight: 800;
}

.hero p {
    color: #C6D6EA;
}

.panel {
    background: white;
    padding: 22px;
    border: 1px solid #E6EAF0;
    border-radius: 16px;
    margin-bottom: 15px;
}

.metric {
    background: white;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #E6EAF0;
}

.metric-label {
    color: #64748B;
    font-size: 13px;
}

.metric-value {
    color: #14243B;
    font-size: 28px;
    font-weight: 800;
}

.highlight {
    padding: 4px 7px;
    border-radius: 6px;
    font-weight: 700;
    border-bottom: 2px solid;
}

div.stButton > button {
    border-radius: 10px;
    font-weight: 600;
    min-height: 43px;
}

.stTextArea textarea {
    border-radius: 12px;
}

footer {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)


# =========================================================
# API
# =========================================================

def backend_status():
    try:
        return requests.get(
            f"{API}/health", timeout=3
        ).ok
    except requests.RequestException:
        return False


def api_request(endpoint, payload):
    try:
        response = requests.post(
            f"{API}/{endpoint}",
            json=payload,
            timeout=240
        )
        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        st.error(f"Backend request failed: {error}")
        return None


# =========================================================
# HIGHLIGHTING
# =========================================================

def highlight_text(text, entities):
    entities = sorted(
        entities,
        key=lambda x: x["start"]
    )

    result = []
    cursor = 0

    for entity in entities:
        start = entity["start"]
        end = entity["end"]

        if start < cursor or end > len(text):
            continue

        label = entity["label"]
        background, foreground = COLORS.get(
            label, ("#E2E8F0", "#334155")
        )

        result.append(html.escape(text[cursor:start]))

        value = html.escape(text[start:end])

        result.append(
            f'<span class="highlight" '
            f'style="background:{background};'
            f'color:{foreground};border-color:{foreground}">'
            f'{value} <small>{label}</small></span>'
        )

        cursor = end

    result.append(html.escape(text[cursor:]))

    return "".join(result)


# =========================================================
# SIDEBAR
# =========================================================

with st.sidebar:
    st.markdown("# 🔐 IndiaPII")
    st.caption("PRIVACY INTELLIGENCE PLATFORM")

    st.divider()

    st.markdown("### Navigation")

    page = st.radio(
        "Workspace",
        ["Detect", "Mask", "Restore", "GenAI Assistant", "Document Intelligence"],
        key="navigation_page",
        label_visibility="collapsed"
    )

    st.session_state.active_page = page

    st.divider()

    st.markdown("### Preferences")

    language = st.selectbox(
        "Input language",
        ["English", "Hindi", "Hinglish"],
        key="language"
    )

    st.divider()

    online = backend_status()

    if online:
        st.success("API Online")
        try:
            ollama_online = requests.get(
                f"{API}/genai/health", timeout=3
            ).ok
        except requests.RequestException:
            ollama_online = False

        if ollama_online:
            st.success("Local GenAI Online")
        else:
            st.warning("Local GenAI Offline")
    else:
        st.error("API Offline")

    st.markdown("### Model information")
    st.info(
        "Fine-tuned MuRIL\n\n"
        "Token classification\n\n"
        "7 PII categories"
    )

    st.caption("IndiaPII · Research Prototype")


# =========================================================
# HERO
# =========================================================

st.markdown("""
<div class="hero">
    <h1>IndiaPII</h1>
    <p>INTELLIGENT MULTILINGUAL PRIVACY PROTECTION</p>
    <h2 style="color:white;">Your data. Your privacy.</h2>
    <p>
        Detect sensitive information, protect it with reversible
        masking and restore it whenever required.
    </p>
</div>
""", unsafe_allow_html=True)


# =========================================================
# TOP METRICS
# =========================================================

m1, m2, m3 = st.columns(3)

for col, title, value in [
    (m1, "SUPPORTED LANGUAGES", "03"),
    (m2, "PII CATEGORIES", "07"),
    (m3, "DETECTION ENGINE", "MuRIL")
]:
    with col:
        st.markdown(
            f"""
            <div class="metric">
                <div class="metric-label">{title}</div>
                <div class="metric-value">{value}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

st.write("")


# =========================================================
# DETECT WORKSPACE
# =========================================================

if page == "Detect":
    st.markdown("## 🔍 Detection workspace")
    st.caption("Analyze text and identify sensitive personal information.")

    # Document upload
    st.markdown("### 📄 Upload a document")
    uploaded_file = st.file_uploader(
        "Upload a text document",
        type=["txt"],
        help="Upload a TXT file containing English, Hindi or Hinglish text.",
        key="document_upload"
    )

    if uploaded_file is not None:
        try:
            uploaded_text = uploaded_file.getvalue().decode("utf-8-sig")
            if st.session_state.input_text != uploaded_text:
                st.session_state.input_text = uploaded_text
                st.session_state.entities = []
                st.session_state.original = ""
                st.session_state.masked = ""
                st.session_state.mapping = {}
                st.session_state.restored = ""
            st.success(f"Loaded {uploaded_file.name} successfully.")
        except UnicodeDecodeError:
            st.error("Unable to read this file. Please upload a UTF-8 text file.")

    sample_col, clear_col = st.columns(2)

    with sample_col:
        if st.button("✨ Load sample text", width="stretch"):
            st.session_state.input_text = SAMPLES[language]
            st.session_state.entities = []
            st.session_state.original = ""
            st.session_state.masked = ""
            st.session_state.mapping = {}
            st.session_state.restored = ""
            st.rerun()

    with clear_col:
        if st.button("↻ Clear workspace", width="stretch"):
            st.session_state.input_text = ""
            st.session_state.entities = []
            st.session_state.original = ""
            st.session_state.masked = ""
            st.session_state.mapping = {}
            st.session_state.restored = ""
            st.rerun()

    text = st.text_area(
        "Enter text to analyze",
        key="input_text",
        height=180,
        placeholder="Type or paste English, Hindi or Hinglish text..."
    )

    st.caption(f"Characters: {len(text)} · Language: {language}")

    if st.button(
        "🔍 Analyze text",
        type="primary",
        width="stretch"
    ):
        if not text.strip():
            st.warning("Enter some text first.")
        elif not online:
            st.error("Start the FastAPI backend first.")
        else:
            with st.spinner("MuRIL is analyzing your text..."):
                result = api_request("detect", {"text": text})

            if result is not None:
                st.session_state.entities = result.get("entities", [])
                st.session_state.original = text
                st.session_state.masked = ""
                st.session_state.mapping = {}
                st.session_state.restored = ""
                st.rerun()

    entities = st.session_state.entities

    if st.session_state.original:
        st.divider()
        st.markdown("### Detection results")

        if not entities:
            st.info("No PII entities detected.")
        else:
            counts = Counter(item["label"] for item in entities)
            c1, c2, c3 = st.columns(3)
            c1.metric("Entities found", len(entities))
            c2.metric("PII categories", len(counts))

            avg = sum(item["score"] for item in entities) / len(entities)
            c3.metric("Average confidence", f"{avg:.1%}")

            st.markdown("### Highlighted text")
            st.markdown(
                f'<div class="panel">{highlight_text(st.session_state.original, entities)}</div>',
                unsafe_allow_html=True
            )

            st.markdown("### Entity breakdown")
            for label, count in counts.items():
                background, foreground = COLORS.get(label, ("#E2E8F0", "#334155"))
                st.markdown(
                    f'<span class="highlight" '
                    f'style="background:{background};color:{foreground};border-color:{foreground}">'
                    f'{label}: {count}</span>',
                    unsafe_allow_html=True
                )

            st.write("")
            details = pd.DataFrame([
                {
                    "Entity": item["label"],
                    "Detected value": item["text"],
                    "Start": item["start"],
                    "End": item["end"],
                    "Confidence": f'{item["score"]:.2%}'
                }
                for item in entities
            ])
            st.dataframe(details, width="stretch", hide_index=True)

            st.button(
                "Continue to masking →",
                on_click=navigate_to,
                args=("Mask",)
            )


# =========================================================
# MASK WORKSPACE
# =========================================================

elif page == "Mask":
    st.markdown("## 🔒 Privacy protection")
    st.caption("Replace detected PII with reversible placeholders.")

    source = st.session_state.original or st.session_state.input_text

    if not source.strip():
        st.info("Enter and detect text first in the Detection workspace.")

    else:
        st.markdown("### Original text")
        st.code(source, language="text")

        if st.button(
            "🔐 Mask sensitive information",
            type="primary",
            width="stretch"
        ):
            with st.spinner("Masking sensitive information..."):
                result = api_request(
                    "mask",
                    {"text": source}
                )

            if result is not None:
                st.session_state.original = source
                st.session_state.masked = result["masked_text"]
                st.session_state.mapping = result["mapping"]
                st.session_state.entities = result.get(
                    "entities", st.session_state.entities
                )
                st.session_state.restored = ""
                st.rerun()

        if st.session_state.masked:
            st.divider()
            st.success("PII masking completed.")

            st.markdown("### Protected output")

            st.code(
                st.session_state.masked,
                language="text"
            )

            st.download_button(
                "⬇ Download masked text",
                data=st.session_state.masked,
                file_name="indiapii_masked.txt",
                mime="text/plain",
                width="stretch"
            )

            st.caption(
                "The reversible mapping is retained in this "
                "browser session. Treat it as sensitive data."
            )

            with st.expander("View mapping"):
                st.json(st.session_state.mapping)

            st.button(
                "Restore this text →",
                on_click=navigate_to,
                args=("Restore",)
            )


# =========================================================
# RESTORE WORKSPACE
# =========================================================

elif page == "Restore":
    st.markdown("## 🔓 Restore original text")
    st.caption("Reverse masking using the original mapping.")

    if not st.session_state.masked:
        st.info("No masked text is available in this session.")

    else:
        st.markdown("### Masked text")

        st.code(
            st.session_state.masked,
            language="text"
        )

        if st.button(
            "🔓 Restore original",
            type="primary",
            width="stretch"
        ):
            result = api_request(
                "unmask",
                {
                    "masked_text": st.session_state.masked,
                    "mapping": st.session_state.mapping
                }
            )

            if result is not None:
                st.session_state.restored = result["restored_text"]
                st.rerun()

        if st.session_state.restored:
            st.success("Original text restored.")

            st.markdown("### Restored result")

            st.code(
                st.session_state.restored,
                language="text"
            )

            if (
                st.session_state.restored
                == st.session_state.original
            ):
                st.success("✓ Round-trip verification passed.")
            else:
                st.warning(
                    "Restored text differs from original text."
                )

            st.download_button(
                "⬇ Download restored text",
                data=st.session_state.restored,
                file_name="indiapii_restored.txt",
                mime="text/plain",
                width="stretch"
            )


# =========================================================
# GENAI ASSISTANT
# =========================================================

elif page == "GenAI Assistant":
    st.markdown("## ✨ GenAI Assistant")
    st.caption(
        "Use local Ollama to summarize, ask questions about, or rewrite "
        "documents after PII has been masked."
    )

    st.info(
        "Privacy workflow: IndiaPII first masks the document using MuRIL. "
        "Only the masked text is sent to your local Ollama model. "
        "The reversible mapping is not sent to GenAI."
    )

    # Prefill from the existing Detect/Mask workflow when available.
    if not st.session_state.genai_input:
        existing_source = (
            st.session_state.original
            or st.session_state.input_text
        )
        if existing_source:
            st.session_state.genai_input = existing_source

    document = st.text_area(
        "Document for the AI assistant",
        key="genai_input",
        height=220,
        placeholder="Paste text or use a document from the Detect workspace..."
    )

    task = st.selectbox(
        "Choose an AI task",
        ["Summarize", "Ask questions", "Rewrite"],
        key="genai_task"
    )

    question = ""
    if task == "Ask questions":
        question = st.text_input(
            "Your question",
            placeholder="What is the purpose of this document?"
        )

    st.caption(
        "Model: llama3.2:3b · Runtime: local Ollama · "
        "Languages: English, Hindi and Hinglish"
    )

    if st.button(
        "✨ Run AI assistant",
        type="primary",
        width="stretch"
    ):
        if not document.strip():
            st.warning("Enter or paste a document first.")
        elif task == "Ask questions" and not question.strip():
            st.warning("Enter a question to continue.")
        elif not online:
            st.error("Start the FastAPI backend first.")
        else:
            with st.spinner("Detecting and masking PII before GenAI..."):
                mask_result = api_request(
                    "mask",
                    {"text": document}
                )

            if mask_result is not None:
                # Keep the masked text for transparency. The mapping is
                # deliberately not included in the GenAI request.
                masked_document = mask_result["masked_text"]
                st.session_state.genai_masked = masked_document

                task_value = {
                    "Summarize": "summarize",
                    "Ask questions": "ask",
                    "Rewrite": "rewrite"
                }[task]

                genai_payload = {
                    "masked_text": masked_document,
                    "task": task_value
                }

                if task_value == "ask":
                    genai_payload["question"] = question.strip()

                with st.spinner("Ollama is processing the masked document..."):
                    ai_result = api_request("genai", genai_payload)

                if ai_result is not None:
                    st.session_state.genai_response = ai_result.get(
                        "response", ""
                    )
                    st.rerun()

    if st.session_state.genai_masked:
        with st.expander("View text sent to local GenAI", expanded=False):
            st.code(
                st.session_state.genai_masked,
                language="text"
            )
            st.caption(
                "This is the masked version. Original PII values and the "
                "reversible mapping are not included in the GenAI request."
            )

    if st.session_state.genai_response:
        st.divider()
        st.markdown("### AI-generated result")
        st.markdown(
            f'<div class="panel">{html.escape(st.session_state.genai_response).replace(chr(10), "<br>")}</div>',
            unsafe_allow_html=True
        )

        st.download_button(
            "⬇ Download AI result",
            data=st.session_state.genai_response,
            file_name="indiapii_ai_result.txt",
            mime="text/plain",
            width="stretch"
        )

        if st.button("Clear AI result"):
            st.session_state.genai_response = ""
            st.session_state.genai_masked = ""
            st.rerun()




# =========================================================
# DOCUMENT INTELLIGENCE (RAG)
# =========================================================

elif page == "Document Intelligence":
    st.markdown("## 📚 Document Intelligence")
    st.caption(
        "Upload a document, protect personal information, then ask questions "
        "using local embeddings and retrieval-augmented generation."
    )

    st.info(
        "Privacy workflow: the document is first processed by MuRIL and "
        "masked through IndiaPII. Only masked text is sent to the local "
        "embedding model and local Llama model. The reversible mapping is "
        "never sent to RAG."
    )

    rag_file = st.file_uploader(
        "Upload a document for RAG",
        type=["txt"],
        help="Upload a UTF-8 TXT document in English, Hindi or Hinglish.",
        key="rag_document_upload"
    )

    rag_text = ""
    rag_name = "document.txt"

    if rag_file is not None:
        rag_name = rag_file.name
        try:
            rag_text = rag_file.getvalue().decode("utf-8-sig")
            st.success(f"Loaded {rag_name} ({len(rag_text)} characters).")
        except UnicodeDecodeError:
            st.error("Unable to read this file. Please upload a UTF-8 text file.")
            rag_text = ""

    with st.expander("Or paste document text"):
        pasted_rag_text = st.text_area(
            "Document text",
            height=180,
            key="rag_pasted_text",
            placeholder="Paste document content here..."
        )
        if pasted_rag_text.strip():
            rag_text = pasted_rag_text
            rag_name = "pasted_document.txt"

    if rag_text.strip():
        st.markdown("#### Document preview")
        st.text_area(
            "Original document (used only for local PII masking)",
            value=rag_text,
            height=140,
            disabled=True,
            key="rag_original_preview"
        )

        if st.button(
            "🔐 Protect and index document",
            type="primary",
            width="stretch",
            disabled=not online
        ):
            # Clear previous document/chat only when a new indexing attempt starts.
            st.session_state.rag_document_id = ""
            st.session_state.rag_document_name = ""
            st.session_state.rag_masked_text = ""
            st.session_state.rag_chat_history = []

            with st.spinner("MuRIL is detecting and masking PII..."):
                mask_result = api_request("mask", {"text": rag_text})

            if mask_result is not None:
                masked_document = mask_result.get("masked_text", "")

                if not masked_document.strip():
                    st.error("Masking returned empty text. Document was not indexed.")
                else:
                    st.session_state.rag_masked_text = masked_document

                    with st.spinner("Nomic is generating embeddings and indexing masked chunks..."):
                        index_result = api_request(
                            "rag/index",
                            {
                                "masked_text": masked_document,
                                "document_name": rag_name
                            }
                        )

                    if index_result is not None:
                        st.session_state.rag_document_id = index_result["document_id"]
                        st.session_state.rag_document_name = index_result.get(
                            "document_name", rag_name
                        )
                        st.success("Document protected and indexed successfully.")
                        st.rerun()

    if st.session_state.rag_document_id:
        st.divider()
        st.markdown("### Indexed document")
        r1, r2, r3 = st.columns(3)
        r1.metric("Document", st.session_state.rag_document_name)
        r2.metric("Indexed chunks", "Ready")
        r3.metric("Embedding model", "Nomic")

        with st.expander("Inspect masked document"):
            st.code(st.session_state.rag_masked_text, language="text")
            st.caption(
                "Only this masked content was indexed. The original-to-placeholder "
                "mapping was not supplied to the embedding or RAG endpoints."
            )

        st.markdown("### 💬 Ask your document")
        rag_question = st.text_input(
            "Ask a question",
            key="rag_question",
            placeholder="e.g. What loan amount was requested?"
        )
        rag_top_k = st.slider(
            "Retrieved sections",
            min_value=1,
            max_value=5,
            value=3,
            help="Number of relevant document chunks supplied to the local LLM."
        )

        if st.button(
            "Ask question",
            type="primary",
            width="stretch",
            disabled=not rag_question.strip()
        ):
            with st.spinner("Retrieving relevant sections and generating an answer..."):
                rag_result = api_request(
                    "rag/ask",
                    {
                        "document_id": st.session_state.rag_document_id,
                        "question": rag_question.strip(),
                        "top_k": rag_top_k
                    }
                )

            if rag_result is not None:
                st.session_state.rag_chat_history.append(
                    {
                        "question": rag_question.strip(),
                        "answer": rag_result.get("answer", ""),
                        "retrieved_chunks": rag_result.get("retrieved_chunks", [])
                    }
                )
                st.rerun()

        if st.session_state.rag_chat_history:
            st.markdown("#### Conversation")
            for index, exchange in enumerate(st.session_state.rag_chat_history, start=1):
                with st.chat_message("user"):
                    st.markdown(exchange["question"])
                with st.chat_message("assistant"):
                    st.markdown(exchange["answer"])

                    retrieved = exchange.get("retrieved_chunks", [])
                    if retrieved:
                        with st.expander(
                            f"View retrieved evidence ({len(retrieved)} sections)"
                        ):
                            for item in retrieved:
                                st.markdown(
                                    f"**Section {item.get('chunk_index', 0) + 1}** "
                                    f"· Similarity: {item.get('score', 'N/A')}"
                                )
                                st.code(item.get("chunk", ""), language="text")

            if st.button("Clear conversation"):
                st.session_state.rag_chat_history = []
                st.rerun()

        st.caption(
            "Prototype limitation: the RAG index is held in FastAPI process memory. "
            "Restarting FastAPI clears indexed documents; index the document again "
            "after a restart."
        )


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.markdown(
    """
    <div style="text-align:center;color:#64748B;padding:15px;">
        <b>IndiaPII</b><br>
        MuRIL-powered multilingual PII detection and reversible masking
        <br><small>English · Hindi · Hinglish | Research Prototype</small>
    </div>
    """,
    unsafe_allow_html=True
)
