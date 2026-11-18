import re
from pathlib import Path

import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MODEL_PATH = PROJECT_ROOT / "models" / "muril-pii"

INDIAN_AMOUNT_PATTERN = re.compile(
    r"(?<!\d)(?:(?:₹|Rs\.?|INR)\s*)?"
    r"\d{1,2}(?:,\d{2})*,\d{3}(?:\.\d{1,2})?(?!\d)",
    re.IGNORECASE,
)

DATE_PATTERN = re.compile(
    r"\b(?:"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
    r"|"
    r"\d{1,2}\s+"
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
    r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    r"\s+\d{4}"
    r")\b",
    re.IGNORECASE,
)

PAN_PATTERN = re.compile(
    r"(?<![A-Z0-9])[A-Z]{5}[0-9]{4}[A-Z](?![A-Z0-9])"
)
AADHAAR_PATTERN = re.compile(r"(?<!\d)[2-9]\d{11}(?!\d)")
EMAIL_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}(?![\w.-])",
    re.IGNORECASE,
)
UPI_PATTERN = re.compile(
    r"(?<![\w.+-])[A-Z0-9._-]{2,}@[A-Z][A-Z0-9.-]{1,}(?![\w.-])",
    re.IGNORECASE,
)

# A labelled PAN field is strong context. Capture the complete identifier
# even if MuRIL splits it into multiple fragments or assigns wrong labels.
PAN_CONTEXT_PATTERN = re.compile(
    r"\bPAN\s*(?:number|no\.?)?\s*[:#-]\s*"
    r"([A-Z]{5}[0-9]{4}[A-Z])\b",
    re.IGNORECASE,
)


def load_pii_pipeline():
    if not MODEL_PATH.exists():
        raise FileNotFoundError(f"MuRIL model not found at: {MODEL_PATH}")

    tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_PATH), local_files_only=True
    )
    model = AutoModelForTokenClassification.from_pretrained(
        str(MODEL_PATH), local_files_only=True
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

    return pipeline(
        "token-classification",
        model=model,
        tokenizer=tokenizer,
        aggregation_strategy="simple",
        device=device,
    )


pii_pipeline = load_pii_pipeline()


def normalize_entity_label(raw_label: str) -> str:
    return re.sub(r"^[BILU]-", "", raw_label.upper())


def numeric_digit_count(value: str) -> int:
    return len(re.sub(r"\D", "", value))


def overlaps_pattern(pattern: re.Pattern, text: str, start: int, end: int) -> bool:
    return any(
        start < match.end() and end > match.start()
        for match in pattern.finditer(text)
    )


def _add_entity(entities, text, start, end, label, score=1.0):
    if 0 <= start < end <= len(text):
        entities.append({
            "start": start,
            "end": end,
            "label": label,
            "text": text[start:end],
            "score": float(score),
        })


def detect_pii(text: str, score_threshold: float = 0.0):
    if not isinstance(text, str):
        raise TypeError("Input text must be a string.")
    if not text.strip():
        return []

    predictions = pii_pipeline(text)
    entities = []

    # Deterministic extraction for explicitly labelled identifiers.
    for match in PAN_CONTEXT_PATTERN.finditer(text):
        start, end = match.span(1)
        _add_entity(entities, text, start, end, "PAN", 1.0)

    aadhaar_context = re.compile(
        r"(?:aadhaar|aadhar|uid)\s*(?:number|no\.?|id)?\s*[:#-]?\s*",
        re.IGNORECASE,
    )
    for context_match in aadhaar_context.finditer(text):
        number_match = AADHAAR_PATTERN.match(text, context_match.end())
        if number_match:
            _add_entity(
                entities, text, number_match.start(), number_match.end(),
                "AADHAAR", 1.0
            )

    upi_context = re.compile(
        r"\bUPI\s*(?:ID|address)?\s*[:#-]\s*", re.IGNORECASE
    )
    for context_match in upi_context.finditer(text):
        upi_match = UPI_PATTERN.match(text, context_match.end())
        if upi_match:
            _add_entity(
                entities, text, upi_match.start(), upi_match.end(),
                "UPI", 1.0
            )

    for match in EMAIL_PATTERN.finditer(text):
        _add_entity(entities, text, match.start(), match.end(), "EMAIL", 1.0)

    for item in predictions:
        start = int(item["start"])
        end = int(item["end"])
        label = normalize_entity_label(
            item.get("entity_group", item.get("entity", ""))
        )
        score = float(item.get("score", 0.0))

        if not (0 <= start < end <= len(text)) or score < score_threshold:
            continue

        detected_text = text[start:end]

        # Reject incomplete PAN predictions. Complete PANs in labelled fields
        # have already been captured by PAN_CONTEXT_PATTERN.
        if label == "PAN":
            pan_match = PAN_PATTERN.search(detected_text)
            if not pan_match:
                continue
            old_start = start
            start = old_start + pan_match.start()
            end = old_start + pan_match.end()
            detected_text = text[start:end]

        # Protect dates and formatted money from numeric model false positives.
        if overlaps_pattern(INDIAN_AMOUNT_PATTERN, text, start, end):
            continue
        if overlaps_pattern(DATE_PATTERN, text, start, end):
            continue

        if label == "PHONE" and numeric_digit_count(detected_text) not in {10, 11, 12}:
            continue
        if label == "AADHAAR" and numeric_digit_count(detected_text) != 12:
            continue

        if label == "PHONE":
            left = max(0, start - 40)
            right = min(len(text), end + 20)
            surrounding = text[left:right].lower()
            if (
                re.fullmatch(r"[2-9]\d{11}", detected_text)
                and re.search(r"aadhaar|aadhar|uid", surrounding)
            ):
                label = "AADHAAR"

        # Ignore model fragments overlapping a complete regex/context match.
        complete_labels = {"PAN", "EMAIL", "UPI", "AADHAAR"}
        if any(
            existing["label"] in complete_labels
            and start < existing["end"]
            and end > existing["start"]
            for existing in entities
        ):
            continue

        _add_entity(entities, text, start, end, label, score)

    # Resolve overlaps by preferring the longest complete span, then confidence.
    entities.sort(
        key=lambda entity: (
            entity["start"],
            -(entity["end"] - entity["start"]),
            -entity["score"],
        )
    )

    selected = []
    for entity in entities:
        if selected and entity["start"] < selected[-1]["end"]:
            previous = selected[-1]
            current_key = (
                entity["end"] - entity["start"], entity["score"]
            )
            previous_key = (
                previous["end"] - previous["start"], previous["score"]
            )
            if current_key > previous_key:
                selected[-1] = entity
            continue
        selected.append(entity)

    return selected
