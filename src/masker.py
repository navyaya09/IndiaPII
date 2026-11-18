
from collections import defaultdict

from .detector import detect_pii, normalize_entity_label


def mask_text(text: str, entities=None):
    if entities is None:
        entities = detect_pii(text)

    # Validate and sort spans
    entities = sorted(
        entities,
        key=lambda x: (x["start"], x["end"])
    )

    for i, entity in enumerate(entities):
        if not (
            0 <= entity["start"] < entity["end"] <= len(text)
        ):
            raise ValueError(
                f"Invalid entity offsets: {entity}"
            )

        if i > 0 and entity["start"] < entities[i - 1]["end"]:
            raise ValueError(
                "Overlapping entity spans detected. "
                "Resolve them before masking."
            )

    counters = defaultdict(int)
    value_to_placeholder = {}
    placeholder_to_value = {}
    replacements = []

    for entity in entities:
        label = normalize_entity_label(entity["label"])
        value = text[entity["start"]:entity["end"]]

        key = (label, value)

        if key not in value_to_placeholder:
            counters[label] += 1

            placeholder = (
                f"[{label}_{counters[label]}]"
            )

            value_to_placeholder[key] = placeholder
            placeholder_to_value[placeholder] = value

        else:
            placeholder = value_to_placeholder[key]

        replacements.append((
            entity["start"],
            entity["end"],
            placeholder
        ))

    # Replace from right to left to preserve offsets
    masked = text

    for start, end, placeholder in reversed(replacements):
        masked = (
            masked[:start]
            + placeholder
            + masked[end:]
        )

    return masked, placeholder_to_value


def unmask_text(masked_text: str, mapping: dict):
    restored = masked_text

    for placeholder in sorted(mapping, key=len, reverse=True):
        restored = restored.replace(
            placeholder,
            mapping[placeholder]
        )

    return restored
