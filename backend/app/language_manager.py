import json
from pathlib import Path


LANGUAGES_DIR = Path(__file__).resolve().parent / "languages"

DEFAULT_SOURCE_LANGUAGE = "ko"
DEFAULT_TARGET_LANGUAGE = "en"


class LanguageManager:

    def __init__(self):
        self.languages_dir = LANGUAGES_DIR

    def get_installed_languages(self):
        languages = []

        if not self.languages_dir.exists():
            return languages

        for manifest_path in sorted(
            self.languages_dir.glob("*/manifest.json")
        ):
            try:
                with manifest_path.open(
                    "r", encoding="utf-8"
                ) as file:
                    manifest = json.load(file)

                required = (
                    "id",
                    "name",
                    "code",
                    "version"
                )

                if not all(key in manifest for key in required):
                    continue

                if manifest.get("enabled", False):
                    languages.append(manifest)

            except (OSError, ValueError):
                continue

        return languages

    def get_language(self, code: str):
        for language in self.get_installed_languages():
            if language["code"] == code:
                return language

        return None

    def is_supported(self, code: str) -> bool:
        return self.get_language(code) is not None


language_manager = LanguageManager()