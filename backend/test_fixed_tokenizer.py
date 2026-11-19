import torch
from transformers import MarianTokenizer, MarianMTModel

MODEL_ID = "Helsinki-NLP/opus-mt-tc-big-en-ko"

print("Loading corrected tokenizer...")

# Load tokenizer from the proposed fix branch
tokenizer = MarianTokenizer.from_pretrained(
    MODEL_ID,
    revision="refs/pr/7"
)

print("Separate vocabularies:", tokenizer.separate_vocabs)
print("Target vocabulary:", len(tokenizer.target_encoder))

print("Loading original model weights...")

# Keep the original model weights
model = MarianMTModel.from_pretrained(MODEL_ID)
model.to("cpu")
model.eval()

model.generation_config.max_length = 128

tests = [
    "Yes.",
    "2, 4, 6 etc. are even numbers.",
    "I'm a little busy right now. Can we talk later?"
]

for text in tests:
    inputs = tokenizer(
        text,
        return_tensors="pt"
    )

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            num_beams=4
        )

    translated = tokenizer.decode(
        output[0],
        skip_special_tokens=True
    )

    print("=" * 50)
    print("English:", text)
    print("Korean:", translated)