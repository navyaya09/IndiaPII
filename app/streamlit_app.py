
import streamlit as st
import requests
import pandas as pd

# ---------------- CONFIGURATION ----------------

API_URL = "http://127.0.0.1:8000"

st.set_page_config(
    page_title="IndiaPII",
    page_icon="🔐",
    layout="wide"
)

# ---------------- SESSION STATE ----------------

if "entities" not in st.session_state:
    st.session_state.entities = []

if "masked_text" not in st.session_state:
    st.session_state.masked_text = ""

if "mapping" not in st.session_state:
    st.session_state.mapping = {}

if "restored_text" not in st.session_state:
    st.session_state.restored_text = ""

# ---------------- API HELPER ----------------

def call_api(endpoint, payload):
    try:
        response = requests.post(
            f"{API_URL}/{endpoint}",
            json=payload,
            timeout=120
        )

        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError:
        st.error(
            "Cannot connect to IndiaPII backend. "
            "Please start FastAPI first."
        )
    except requests.exceptions.Timeout:
        st.error("The request timed out.")
    except requests.exceptions.HTTPError:
        st.error(
            f"API error: {response.status_code} - "
            f"{response.text}"
        )
    except requests.exceptions.RequestException as e:
        st.error(f"Request failed: {e}")

    return None


# ---------------- HEADER ----------------

st.title("🔐 IndiaPII")
st.subheader(
    "Indian Multilingual PII Detection and Reversible Masking"
)

st.markdown(
    """
    Detect and protect sensitive personal information in
    **English, Hindi and Hinglish** using a fine-tuned MuRIL model.
    """
)

st.divider()

# ---------------- BACKEND STATUS ----------------

try:
    health = requests.get(
        f"{API_URL}/health",
        timeout=5
    )

    if health.ok:
        st.success("IndiaPII backend connected")
    else:
        st.warning("Backend health check failed")

except requests.exceptions.RequestException:
    st.error("Backend offline. Start FastAPI in another terminal.")

# ---------------- INPUT ----------------

st.markdown("### Enter your text")

sample = (
    "My name is Rahul Sharma and "
    "my email is rahul@example.com."
)

text_input = st.text_area(
    "Text to analyze",
    height=150,
    placeholder="Enter English, Hindi or Hinglish text..."
)

col1, col2 = st.columns([1, 1])

with col1:
    detect_button = st.button(
        "🔍 Detect PII",
        use_container_width=True
    )

with col2:
    mask_button = st.button(
        "🔒 Mask PII",
        use_container_width=True
    )

# ---------------- DETECTION ----------------

if detect_button:
    if not text_input.strip():
        st.warning("Please enter some text first.")
    else:
        result = call_api(
            "detect",
            {"text": text_input}
        )

        if result is not None:
            st.session_state.entities = result["entities"]
            st.session_state.masked_text = ""
            st.session_state.mapping = {}
            st.session_state.restored_text = ""

# ---------------- MASKING ----------------

if mask_button:
    if not text_input.strip():
        st.warning("Please enter some text first.")
    else:
        result = call_api(
            "mask",
            {"text": text_input}
        )

        if result is not None:
            st.session_state.entities = [
                {
                    "label": label
                }
                for label in result["entity_labels"]
            ] if not st.session_state.entities else st.session_state.entities

            st.session_state.masked_text = result["masked_text"]
            st.session_state.mapping = result["mapping"]
            st.session_state.restored_text = ""

# ---------------- DETECTION RESULTS ----------------

if st.session_state.entities:
    st.divider()
    st.markdown("### Detection Results")

    st.metric(
        "Detected PII entities",
        len(st.session_state.entities)
    )

    entity_df = pd.DataFrame(
        st.session_state.entities
    )

    st.dataframe(
        entity_df,
        use_container_width=True,
        hide_index=True
    )

# ---------------- MASKED OUTPUT ----------------

if st.session_state.masked_text:
    st.divider()
    st.markdown("### 🔒 Masked Output")

    st.code(
        st.session_state.masked_text,
        language="text"
    )

    st.success("Sensitive information masked successfully.")

    st.caption(
        "The reversible mapping is retained in this browser session "
        "for restoration. Do not expose or share it."
    )

    # ---------------- RESTORATION ----------------

    if st.button(
        "🔓 Restore Original Text",
        use_container_width=True
    ):
        result = call_api(
            "unmask",
            {
                "masked_text": st.session_state.masked_text,
                "mapping": st.session_state.mapping
            }
        )

        if result is not None:
            st.session_state.restored_text = (
                result["restored_text"]
            )

    if st.session_state.restored_text:
        st.markdown("### Restored Original Text")

        st.code(
            st.session_state.restored_text,
            language="text"
        )

        st.success("Original text restored successfully.")

# ---------------- FOOTER ----------------

st.divider()

st.caption(
    "IndiaPII | MuRIL-based multilingual PII detection | "
    "Reversible masking"
)
