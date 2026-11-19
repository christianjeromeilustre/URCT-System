from pathlib import Path
from time import perf_counter

import ctranslate2
from transformers import AutoTokenizer

MODEL_ID = "Helsinki-NLP/opus-mt-tc-big-en-ko"

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "opus-en-ko-int8"
)

TEXT = "Hello! How are you today?"

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

print("Loading CTranslate2 model...")
translator = ctranslate2.Translator(
    str(MODEL_PATH),
    device="cpu",
    compute_type="int8",
    inter_threads=1,
    intra_threads=2
)

source_tokens = tokenizer.convert_ids_to_tokens(
    tokenizer.encode(TEXT)
)

# 모델 준비 테스트
print("Warming up...")
translator.translate_batch(
    [source_tokens],
    beam_size=2,
    max_decoding_length=128
)

times = []

for i in range(3):
    start = perf_counter()

    result = translator.translate_batch(
        [source_tokens],
        beam_size=2,
        max_decoding_length=128
    )

    elapsed = perf_counter() - start
    times.append(elapsed)

    target_tokens = result[0].hypotheses[0]

    translated = tokenizer.decode(
        tokenizer.convert_tokens_to_ids(target_tokens),
        skip_special_tokens=True
    )

    print(f"Test {i + 1}: {elapsed:.3f} seconds")
    print(f"Translation: {translated}")
    print("-" * 40)

print(f"Average: {sum(times) / len(times):.3f} seconds")