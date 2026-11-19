from time import perf_counter

import torch
from transformers import (
    MarianMTModel,
    MarianTokenizer
)

MODEL_ID = "Helsinki-NLP/opus-mt-tc-big-en-ko"

sentences = [
    "Yes.",
    "2, 4, 6 etc. are even numbers.",
    "I'm a little busy right now. Can we talk later?"
]

torch.set_num_threads(2)

print("Loading original PyTorch model...")

tokenizer = MarianTokenizer.from_pretrained(MODEL_ID)
model = MarianMTModel.from_pretrained(MODEL_ID)

model.to("cpu")
model.eval()

print("Model loaded successfully.")

for text in sentences:
    inputs = tokenizer(
        text,
        return_tensors="pt",
        truncation=True
    )

    start = perf_counter()

    with torch.inference_mode():
        output = model.generate(
            **inputs,
            num_beams=4,
            max_new_tokens=128
        )

    elapsed = perf_counter() - start

    translated = tokenizer.decode(
        output[0],
        skip_special_tokens=True
    )

    print("=" * 45)
    print("English:", text)
    print("Korean:", translated)
    print(f"Time: {elapsed:.3f} seconds")