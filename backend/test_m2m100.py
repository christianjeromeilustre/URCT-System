from pathlib import Path
from time import perf_counter

import ctranslate2
from transformers import AutoTokenizer

MODEL_ID = "facebook/m2m100_418M"

MODEL_DIR = (
    Path(__file__).resolve().parent.parent
    / "models"
    / "m2m100-int8"
)

print("Loading M2M100 tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

print("Loading M2M100 INT8 model...")
translator = ctranslate2.Translator(
    str(MODEL_DIR),
    device="cpu",
    compute_type="int8",
    inter_threads=1,
    intra_threads=2
)

tests = [
    ("en", "ko", "Yes."),
    ("en", "ko", "I'm a little busy right now. Can we talk later?"),
    ("ko", "en", "안녕하세요. 오늘 하루는 어땠어요?")
]

for source_lang, target_lang, text in tests:

    tokenizer.src_lang = source_lang

    source_tokens = tokenizer.convert_ids_to_tokens(
        tokenizer.encode(text)
    )

    target_prefix = [
        tokenizer.lang_code_to_token[target_lang]
    ]

    start = perf_counter()

    result = translator.translate_batch(
        [source_tokens],
        target_prefix=[target_prefix],
        beam_size=4,
        max_decoding_length=96
    )

    elapsed = perf_counter() - start

    # Remove the forced target-language token.
    output_tokens = result[0].hypotheses[0][1:]

    output_ids = tokenizer.convert_tokens_to_ids(
        output_tokens
    )

    translated = tokenizer.decode(
        output_ids,
        skip_special_tokens=True
    )

    print("=" * 55)
    print("Direction:", source_lang, "->", target_lang)
    print("Original:", text)
    print("Translation:", translated)
    print(f"Time: {elapsed:.3f} seconds")