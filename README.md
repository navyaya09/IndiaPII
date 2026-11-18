# IndiaPII — Indian Multilingual PII Detection and Reversible Masking

**A privacy-aware document intelligence platform for detecting, protecting and working with Personally Identifiable Information (PII) in Indian multilingual text.**

IndiaPII combines multilingual Named Entity Recognition (NER), rule-based detection, reversible masking and locally hosted Generative AI with Retrieval-Augmented Generation (RAG).

The system is designed to process English, Hindi and Hinglish text while preserving useful document information such as financial amounts and dates.

## Key Features

- **Multilingual PII Detection:** Fine-tuned MuRIL model for identifying sensitive entities in English, Hindi and Hinglish.
- **Baseline Comparison:** Regex and Microsoft Presidio-based detection for performance comparison.
- **Indian PII Handling:** Detection and correction logic for Aadhaar, PAN, Indian phone numbers, email addresses, UPI IDs, names and addresses.
- **Reversible Masking:** Replaces sensitive information with typed placeholders and maintains a mapping for restoration.
- **Local GenAI:** Uses Ollama and Llama 3.2 for privacy-aware text summarisation, question answering and rewriting.
- **Document Intelligence:** Uses local embeddings and vector similarity retrieval to answer questions about protected documents.
- **Interactive Interface:** Streamlit application with separate workspaces for detection, masking, restoration, GenAI and document intelligence.
- **REST API:** FastAPI backend exposing detection, masking, restoration and AI endpoints.

## Technology Stack

| Component | Technology |
|---|---|
| Programming language | Python |
| Multilingual NER | Google MuRIL |
| Baselines | Regex, Microsoft Presidio |
| Deep learning | PyTorch, Hugging Face Transformers |
| Backend | FastAPI |
| Frontend | Streamlit |
| Local LLM | Ollama, Llama 3.2 |
| Embeddings | Nomic Embed Text |
| Retrieval | Cosine similarity |
| Data processing | NumPy, Pandas |
| Evaluation | Precision, Recall, F1-score |

## System Architecture

```mermaid
flowchart TD
    A[User Input / Document] --> B[Streamlit Interface]
    B --> C[FastAPI Backend]
    C --> D[PII Detection]
    D --> E[MuRIL NER]
    D --> F[Regex / Presidio Baselines]
    E --> G[Entity Validation and Correction]
    F --> G
    G --> H[Reversible Masking]
    H --> I[Protected Text]
    I --> J[Local GenAI]
    I --> K[Document Chunking]
    K --> L[Nomic Embeddings]
    L --> M[Similarity Retrieval]
    M --> N[Local Llama 3.2]
    N --> O[Grounded Answer]
    H --> P[Secure Mapping]
    P --> Q[Restoration]
```

## PII Categories

The project supports seven entity categories:

- PERSON
- ADDRESS
- PHONE
- AADHAAR
- PAN
- EMAIL
- UPI

The detector also applies validation and contextual corrections to reduce incorrect masking of dates and Indian financial amounts.

## Application Workspaces

| Workspace | Function |
|---|---|
| Detect | Identifies PII entities and displays detection results |
| Mask | Replaces detected PII with typed placeholders |
| Restore | Reconstructs original text using the reversible mapping |
| GenAI Assistant | Summarises, answers questions and rewrites protected text |
| Document Intelligence | Indexes protected documents and answers questions using RAG |

## RAG Workflow

1. The user uploads or enters a document.
2. The original document is passed through the PII detection and masking pipeline.
3. Only the masked document is sent to the RAG indexing component.
4. The document is divided into overlapping text chunks.
5. Nomic Embed Text generates local embeddings.
6. Question embeddings are compared with document embeddings using cosine similarity.
7. Relevant chunks are retrieved.
8. Llama 3.2 generates an answer using the retrieved protected context.

The current RAG index is held in FastAPI process memory and is cleared when the server restarts. Persistent indexing is a planned improvement.

## Model Evaluation

The project compares three PII detection approaches:

- Regex-based detection
- Microsoft Presidio
- Fine-tuned MuRIL

Evaluation includes entity-level precision, recall and F1-score, along with language-wise performance.

The current experiments use a synthetic multilingual dataset. Reported performance should therefore be interpreted in the context of the dataset size and distribution, rather than as a guarantee of real-world accuracy.

## Project Structure

```text
IndiaPII/
├── app/
│   └── streamlit_app.py
├── src/
│   ├── api.py
│   ├── detector.py
│   ├── masker.py
│   └── rag.py
├── models/
│   └── muril-pii/
├── data/
│   ├── raw/
│   └── processed/
├── notebooks/
├── results/
│   └── comparison/
├── test_masking.py
├── requirements.txt
└── README.md
```

Model weights and sensitive datasets should not be committed to GitHub.

## Installation and Setup

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd IndiaPII
```

### 2. Create a virtual environment

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set up the local models

Place the fine-tuned MuRIL model in:

```text
models/muril-pii/
```

Install and start Ollama. Pull the required models:

```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text:latest
```

### 5. Start the FastAPI backend

```bash
uvicorn src.api:app --reload
```

API documentation:

```text
http://127.0.0.1:8000/docs
```

### 6. Start the Streamlit application

Open a separate terminal:

```bash
cd ~/IndiaPII
source .venv/bin/activate
streamlit run app/streamlit_app.py --server.port 8501
```

Open:

```text
http://localhost:8501
```

## API Endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Backend health |
| POST | `/detect` | Detect PII |
| POST | `/mask` | Mask PII |
| POST | `/unmask` | Restore original text |
| GET | `/genai/health` | Check local GenAI availability |
| POST | `/genai` | GenAI tasks |
| POST | `/rag/index` | Index masked document |
| POST | `/rag/ask` | Ask document questions |
| POST | `/rag/delete` | Delete indexed document |

## Privacy Considerations and Limitations

- Original PII should not be sent to the local LLM or embedding model.
- Reversible mappings are sensitive and should be protected.
- The current RAG index is in-memory and does not persist across FastAPI restarts.
- Local execution does not by itself guarantee complete security.
- MuRIL predictions and heuristic corrections may produce false positives and false negatives.
- Synthetic-data evaluation does not establish performance on all real-world Indian documents.

## Future Improvements

- Persistent and scalable vector storage.
- Improved multilingual retrieval and reranking.
- Expanded real-world and domain-specific evaluation.
- Stronger mapping encryption and access controls.
- Document lifecycle management and audit logging.
- Deployment and performance optimisation.

## Project Status

**Research prototype — core detection, reversible masking, local GenAI and RAG workflows implemented.**

Further validation, persistent storage, security hardening and deployment remain areas for improvement.
