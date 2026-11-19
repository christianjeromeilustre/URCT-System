import asyncio
import logging
from time import perf_counter

logger = logging.getLogger(__name__)


class OpusProvider:
    name = "opus"

    MODELS = {
        ("ko", "en"): "Helsinki-NLP/opus-mt-ko-en",
        ("en", "ko"): "Helsinki-NLP/opus-mt-tc-big-en-ko",
    }

    def __init__(self):
        self.loaded_models = {}
        self._lock = asyncio.Lock()
        self._inference_lock = asyncio.Lock()

    def _load_model(self, model_id):
        import torch
        from transformers import (
            AutoTokenizer,
            AutoModelForSeq2SeqLM
        )

        torch.set_num_threads(2)

        logger.info("Loading OPUS-MT: %s", model_id)

        tokenizer = AutoTokenizer.from_pretrained(model_id)

        model = AutoModelForSeq2SeqLM.from_pretrained(
            model_id
        )

        model = model.to("cpu")
        model.eval()

        return tokenizer, model

    async def _get_model(self, model_id):
        async with self._lock:
            if model_id not in self.loaded_models:
                self.loaded_models[model_id] = (
                    await asyncio.to_thread(
                        self._load_model,
                        model_id
                    )
                )

            return self.loaded_models[model_id]

    def _translate_sync(self, text, tokenizer, model):
        import torch

        inputs = tokenizer(
            [text],
            return_tensors="pt",
            truncation=True,
            max_length=256
        )

        with torch.inference_mode():
            output = model.generate(
                **inputs,
                max_new_tokens=128,
                num_beams=2
            )

        return tokenizer.batch_decode(
            output,
            skip_special_tokens=True
        )[0]

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str | None:

        if source_language == target_language:
            return text

        pair = (source_language, target_language)

        if pair not in self.MODELS:
            raise ValueError(
                f"Unsupported language pair: {pair}"
            )

        model_id = self.MODELS[pair]

        async with self._inference_lock:
            tokenizer, model = await self._get_model(
                model_id
            )

            started = perf_counter()

            translated = await asyncio.to_thread(
                self._translate_sync,
                text,
                tokenizer,
                model
            )

            elapsed = perf_counter() - started

            logger.info(
                "OPUS translation time: %.3f seconds",
                elapsed
            )

            return translated