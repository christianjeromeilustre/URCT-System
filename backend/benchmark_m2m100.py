import csv
import json
from pathlib import Path
from statistics import mean
from time import perf_counter

import ctranslate2
from transformers import AutoTokenizer


ROOT = Path(__file__).resolve().parent.parent

TEST_FILE = ROOT / "tests/translation/test_cases.json"
MODEL_PATH = ROOT / "models/m2m100-int8"
RESULT_DIR = ROOT / "tests/translation/results"

RESULT_DIR.mkdir(parents=True, exist_ok=True)

MODEL_ID = "facebook/m2m100_418M"

print("Loading M2M100...")

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

translator = ctranslate2.Translator(
    str(MODEL_PATH),
    device="cpu",
    compute_type="int8",
    inter_threads=1,
    intra_threads=2
)

with TEST_FILE.open("r", encoding="utf-8") as f:
    cases = json.load(f)


def translate(text, source_lang, target_lang):
    tokenizer.src_lang = source_lang

    source_tokens = tokenizer.convert_ids_to_tokens(
        tokenizer.encode(text)
    )

    target_token = tokenizer.lang_code_to_token[target_lang]

    started = perf_counter()

    result = translator.translate_batch(
        [source_tokens],
        target_prefix=[[target_token]],
        beam_size=4,
        max_decoding_length=128
    )

    elapsed = perf_counter() - started

    output_tokens = result[0].hypotheses[0]

    # Remove forced language token if present.
    if output_tokens and output_tokens[0] == target_token:
        output_tokens = output_tokens[1:]

    output_ids = tokenizer.convert_tokens_to_ids(
        output_tokens
    )

    translated = tokenizer.decode(
        output_ids,
        skip_special_tokens=True
    )

    return translated, elapsed


# Warm up both translation directions.
for src, tgt, text in [
    ("ko", "en", "안녕하세요."),
    ("en", "ko", "Hello.")
]:
    translate(text, src, tgt)


results = []

for case in cases:
    src = case["source_language"]
    tgt = case["target_language"]
    text = case["text"]

    print("=" * 55)
    print("Test:", case["id"])
    print("Category:", case["category"])
    print("Original:", text)

    times = []

    try:
        for _ in range(3):
            translated, elapsed = translate(text, src, tgt)
            times.append(elapsed)

        avg_time = mean(times)
        error = ""

    except Exception as exc:
        translated = ""
        avg_time = None
        error = str(exc)

    print("Translation:", translated)
    print("Reference:", case["reference"])
    print("Average time:", avg_time)
    print("Error:", error or "None")

    results.append({
        "id": case["id"],
        "category": case["category"],
        "direction": f"{src}->{tgt}",
        "original": text,
        "translation": translated,
        "reference": case["reference"],
        "avg_seconds": (
            round(avg_time, 3)
            if avg_time is not None else ""
        ),
        "error": error,
        "provider": "m2m100-int8"
    })


output_file = (
    RESULT_DIR / "benchmark_m2m100.csv"
)

with output_file.open(
    "w", newline="", encoding="utf-8-sig"
) as f:
    writer = csv.DictWriter(
        f,
        fieldnames=results[0].keys()
    )
    writer.writeheader()
    writer.writerows(results)

print("=" * 55)
print("Benchmark completed.")
print("Saved:", output_file)