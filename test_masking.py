
from src.detector import detect_pii
from src.masker import mask_text, unmask_text

sample_text = (
    "My name is Rahul Sharma and "
    "my email is rahul@example.com."
)

# Detection
entities = detect_pii(sample_text)

print("\nDetected entities:")
for entity in entities:
    print(entity)

# Masking
masked_text, mapping = mask_text(sample_text, entities)

print("\nMasked text:")
print(masked_text)

print("\nMapping:")
print(mapping)

# Restoration
restored_text = unmask_text(masked_text, mapping)

print("\nRestored text:")
print(restored_text)

assert restored_text == sample_text

print("\nAll detection and masking checks passed!")
