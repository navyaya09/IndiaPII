
import re
from pathlib import Path

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline,
)

# Project configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "muril-pii"

# Load model once and reuse it
def load_pii_pipeline():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"MuRIL model not found at: {MODEL_PATH}"
        )

    tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_PATH),
        local_files_only=True
    )

    model = AutoModelForTokenClassification.from_pretrained(
        str(MODEL_PATH),
        local_files_only=True
    )

    if torch.backends.mps.is_available():
        device = torch.device("mps")
        print("IndiaPII: Using Apple MPS GPU")
    elif torch.cuda.is_available():
        device = 0
        print("IndiaPII: Using CUDA GPU")
    else:
        device = -1
        print("IndiaPII: Using CPU")

    ner_pipeline = pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
        device=device
    )

    return ner_pipeline


# Initialize once
pii_pipeline = load_pii_pipeline()


def normalize_entity_label(raw_label: str) -> str:
    label = raw_label.upper()
    label = re.sub(r"^[BILU]-", "", label)
    return label


def detect_pii(text: str, score_threshold: float = 0.0):
    if not isinstance(text, str):
        raise TypeError("Input text must be a string.")

    if not text.strip():
        return []

    predictions = pii_pipeline(text)
    entities = []

    for item in predictions:
        start = int(item["start"])
        end = int(item["end"])

        label = normalize_entity_label(
            item.get("entity_group", item.get("entity", ""))
        )

        score = float(item.get("score", 0.0))

        if start < 0 or end > len(text) or start >= end:
            continue

        if score < score_threshold:
            continue

        # PAN boundary correction
        if label == "PAN":
            detected_text = text[start:end]

            match = re.search(
                r"[A-Z]{5}[0-9]{4}[A-Z]",
                detected_text
            )

            if match:
                original_start = start
                start = original_start + match.start()
                end = original_start + match.end()

        entities.append({
            "start": start,
            "end": end,
            "label": label,
            "text": text[start:end],
            "score": score,
        })

    # Resolve overlapping predictions
    entities.sort(
        key=lambda x: (
            x["start"],
            -(x["end"] - x["start"]),
            -x["score"]
        )
    )

    selected = []

    for entity in entities:
        if selected and entity["start"] < selected[-1]["end"]:
            if entity["score"] > selected[-1]["score"]:
                selected[-1] = entity
            continue

        selected.append(entity)

    return selected
