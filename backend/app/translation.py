
from dataclasses import dataclass
from typing import Protocol
from app.providers.opus_provider import OpusProvider


# -----------------------------------------
# 1. Translation result
# -----------------------------------------

@dataclass
class TranslationResult:
    original_text: str
    translated_text: str | None
    source_language: str
    target_language: str
    engine: str
    translation_success: bool


# -----------------------------------------
# 2. Translation provider interface
# -----------------------------------------

class TranslationProvider(Protocol):
    name: str

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str | None:
        ...


# -----------------------------------------
# 3. Demonstration provider
# -----------------------------------------

class DemoProvider:
    name = "demo"

    TRANSLATIONS = {
        ("ko", "en", "안녕하세요."): "Hello.",
        ("ko", "en", "만나서 반갑습니다."):
            "Nice to meet you.",
        ("ko", "en", "오늘 기분이 어떻습니까?"):
            "How are you feeling today?",
        ("en", "ko", "Hello."): "안녕하세요.",
        ("en", "ko", "Nice to meet you."):
            "만나서 반갑습니다."
    }

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> str | None:

        if source_language == target_language:
            return text

        return self.TRANSLATIONS.get(
            (source_language, target_language, text)
        )


# -----------------------------------------
# 4. Translation service
# -----------------------------------------

class TranslationService:

    def __init__(self):
        self.providers: dict[str, TranslationProvider] = {}
        self.active_provider = "demo"

    def register(self, provider: TranslationProvider):
        self.providers[provider.name] = provider

    async def translate(
        self,
        text: str,
        source_language: str,
        target_language: str
    ) -> TranslationResult:

        provider = self.providers[self.active_provider]

        translated = await provider.translate(
            text,
            source_language,
            target_language
        )

        return TranslationResult(
            original_text=text,
            translated_text=translated,
            source_language=source_language,
            target_language=target_language,
            engine=provider.name,
            translation_success=translated is not None
        )


# -----------------------------------------
# 5. Initialize translation service
# -----------------------------------------

translation_service = TranslationService()

translation_service.register(DemoProvider())
translation_service.register(OpusProvider())

translation_service.active_provider = "opus"
