
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from src.detector import detect_pii
from src.masker import mask_text, unmask_text

app = FastAPI(
    title="IndiaPII API",
    description="Indian multilingual PII detection and reversible masking",
    version="1.0.0"
)


class TextRequest(BaseModel):
    text: str = Field(..., min_length=1)


class UnmaskRequest(BaseModel):
    masked_text: str = Field(..., min_length=1)
    mapping: dict[str, str]


@app.get("/")
def root():
    return {
        "message": "IndiaPII API is running",
        "status": "active"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/detect")
def detect(request: TextRequest):
    try:
        entities = detect_pii(request.text)
        return {
            "entities": entities,
            "entity_count": len(entities)
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="PII detection failed"
        ) from e


@app.post("/mask")
def mask(request: TextRequest):
    try:
        entities = detect_pii(request.text)
        masked_text, mapping = mask_text(
            request.text,
            entities
        )

        return {
            "masked_text": masked_text,
            "mapping": mapping,
            "entity_count": len(entities),
            "entity_labels": [
                entity["label"] for entity in entities
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="PII masking failed"
        ) from e


@app.post("/unmask")
def unmask(request: UnmaskRequest):
    try:
        restored = unmask_text(
            request.masked_text,
            request.mapping
        )

        return {"restored_text": restored}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail="PII restoration failed"
        ) from e
