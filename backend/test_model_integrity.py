import ctranslate2
from transformers import AutoTokenizer
from pathlib import Path
from time import perf_counter

MODEL_ID = "Helsinki-NLP/opus-mt-tc-big-en-ko"

MODEL_PATH = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "opus-en-ko-int8"
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

translator = ctranslate2.Translator(
    str(MODEL_PATH),
    device="cpu",
    compute_type="int8",
    inter_threads=1,
    intra_threads=2
)

sentences = [
    "Yes.",
    "2, 4, 6 etc. are even numbers.",
    "I'm a little busy right now. Can we talk later?"
]

for sentence in sentences:
    tokens = tokenizer.convert_ids_to_tokens(
        tokenizer.encode(sentence)
    )

    start = perf_counter()

    result = translator.translate_batch(
        [tokens],
        beam_size=4,
        max_decoding_length=128
    )

    elapsed = perf_counter() - start

    output_ids = tokenizer.convert_tokens_to_ids(
        result[0].hypotheses[0]
    )

    translation = tokenizer.decode(
        output_ids,
        skip_special_tokens=True
    )

    print("English:", sentence)
    print("Korean:", translation)
    print(f"Time: {elapsed:.2f} seconds")
    print("-" * 40)