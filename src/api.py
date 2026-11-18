import json
import re
import urllib.error
import urllib.request
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.detector import detect_pii
from src.masker import mask_text, unmask_text
from src.rag import (
    answer_question,
    delete_document,
    index_masked_document,
)

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "llama3.2:3b"

app = FastAPI(
    title="IndiaPII API",
    description="Indian multilingual PII detection, reversible masking and privacy-aware local GenAI",
    version="3.0.0",
)


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)


class UnmaskRequest(BaseModel):
    masked_text: str = Field(..., min_length=1)
    mapping: dict[str, str]


class GenAIRequest(BaseModel):
    masked_text: str = Field(..., min_length=1)
    task: Literal["summarize", "ask", "rewrite"]
    question: Optional[str] = None


class RAGIndexRequest(BaseModel):
    masked_text: str = Field(..., min_length=1)
    document_name: str = Field(default="document.txt", max_length=200)


class RAGQuestionRequest(BaseModel):
    document_id: str = Field(..., min_length=1)
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=3, ge=1, le=5)


class RAGDeleteRequest(BaseModel):
    document_id: str = Field(..., min_length=1)


def call_ollama(masked_text: str, task: str, question: Optional[str] = None):
    prompts = {
        "summarize": (
            "Write a concise summary in 2-3 bullet points. Do not copy the "
            "input verbatim unless it is already extremely short. Preserve "
            "relevant PII placeholders exactly; never infer their values."
        ),
        "ask": (
            "Answer the question using only the supplied text. If the answer "
            "is absent, say so. Preserve relevant placeholders exactly."
        ),
        "rewrite": (
            "Rewrite the text professionally and clearly. Preserve every "
            "PII placeholder exactly. Do not infer or reveal original values."
        ),
    }
    prompt = prompts[task]
    if task == "ask":
        prompt += f"\n\nQuestion: {question}"
    prompt += f"\n\nText:\n{masked_text}"

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a privacy-aware assistant running locally. "
                    "Treat PII placeholders as protected identifiers."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    request = urllib.request.Request(
        OLLAMA_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
        answer = result.get("message", {}).get("content", "").strip()
        if not answer:
            raise RuntimeError("Ollama returned an empty response.")
        return answer
    except urllib.error.URLError as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to local Ollama. Check that it is running.",
        ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Local GenAI processing failed.") from exc


@app.get("/")
def root():
    return {"message": "IndiaPII API is running", "status": "active"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/genai/health")
def genai_health():
    try:
        request = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(request, timeout=5) as response:
            data = json.loads(response.read().decode("utf-8"))
        return {
            "status": "connected",
            "model": OLLAMA_MODEL,
            "available_models": [model["name"] for model in data.get("models", [])],
        }
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Ollama is not reachable.") from exc


@app.post("/detect")
def detect(request: TextRequest):
    try:
        entities = detect_pii(request.text)
        return {"entities": entities, "entity_count": len(entities)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="PII detection failed") from exc


@app.post("/mask")
def mask(request: TextRequest):
    try:
        entities = detect_pii(request.text)
        masked_text, mapping = mask_text(request.text, entities)
        return {
            "masked_text": masked_text,
            "mapping": mapping,
            "entity_count": len(entities),
            "entity_labels": [entity["label"] for entity in entities],
            "entities": entities,
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail="PII masking failed") from exc


@app.post("/unmask")
def unmask(request: UnmaskRequest):
    try:
        restored = unmask_text(request.masked_text, request.mapping)
        return {"restored_text": restored}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="PII restoration failed") from exc


@app.post("/genai")
def genai(request: GenAIRequest):
    if request.task == "ask" and not request.question:
        raise HTTPException(status_code=400, detail="A question is required for the ask task.")
    response = call_ollama(request.masked_text, request.task, request.question)
    return {
        "task": request.task,
        "response": response,
        "model": OLLAMA_MODEL,
        "privacy": "Only masked text was sent to local Ollama.",
    }


@app.post("/rag/index")
def rag_index(request: RAGIndexRequest):
    try:
        return index_masked_document(request.masked_text, request.document_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG indexing failed: {exc}") from exc


@app.post("/rag/ask")
def rag_ask(request: RAGQuestionRequest):
    try:
        return answer_question(request.document_id, request.question, request.top_k)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"RAG question failed: {exc}") from exc


@app.post("/rag/delete")
def rag_delete(request: RAGDeleteRequest):
    deleted = delete_document(request.document_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"status": "deleted", "document_id": request.document_id}
