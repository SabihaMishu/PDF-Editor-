import re
import logging
from typing import Optional
from fastapi import HTTPException, status
from deep_translator import MyMemoryTranslator, GoogleTranslator

logger = logging.getLogger(__name__)

# Common mapping from ISO 639-1 to MyMemory region formats
MYMEMORY_LOCALE_MAP = {
    "en": "en-US",
    "bn": "bn-IN",
    "es": "es-ES",
    "fr": "fr-FR",
    "de": "de-DE",
    "hi": "hi-IN",
    "ar": "ar-SA",
    "zh": "zh-CN",
    "ja": "ja-JP",
    "ru": "ru-RU",
    "pt": "pt-PT",
    "it": "it-IT",
}

class TranslationService:
    @staticmethod
    def _normalize_code(code: str, provider: str = "mymemory") -> str:
        cleaned = code.strip().lower()
        if provider == "mymemory":
            if "-" in cleaned:
                return cleaned
            return MYMEMORY_LOCALE_MAP.get(cleaned, cleaned)
        elif provider == "google":
            return cleaned.split("-")[0]
        return cleaned

    @classmethod
    def _chunk_text(cls, text: str, max_chunk_size: int = 400) -> list[str]:
        """
        Splits text into chunks <= max_chunk_size characters,
        prioritizing sentence and line boundaries.
        """
        lines = text.split("\n")
        chunks: list[str] = []
        for line in lines:
            line = line.strip()
            if not line:
                chunks.append("")
                continue
            if len(line) <= max_chunk_size:
                chunks.append(line)
            else:
                sentences = re.split(r"(?<=[.!?।])\s+", line)
                current_chunk = ""
                for sent in sentences:
                    if len(current_chunk) + len(sent) + 1 <= max_chunk_size:
                        current_chunk = f"{current_chunk} {sent}".strip() if current_chunk else sent
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = sent
                if current_chunk:
                    chunks.append(current_chunk)
        return chunks

    @classmethod
    def translate_chunk(cls, chunk: str, source_lang: str, target_lang: str) -> str:
        """
        Translates a single text segment using MyMemory with fallback to GoogleTranslator.
        If all providers fail, returns the original chunk unchanged.
        """
        if not chunk or not chunk.strip():
            return chunk
        if source_lang.strip().lower() == target_lang.strip().lower():
            return chunk
        # Primary: MyMemoryTranslator
        try:
            mm_src = cls._normalize_code(source_lang, "mymemory")
            mm_tgt = cls._normalize_code(target_lang, "mymemory")
            translator = MyMemoryTranslator(source=mm_src, target=mm_tgt)
            result = translator.translate(chunk)
            if result:
                return result
        except Exception as e:
            logger.warning(f"MyMemory translation failed: {e}. Trying Google fallback...")
        # Fallback: GoogleTranslator
        try:
            g_src = cls._normalize_code(source_lang, "google")
            g_tgt = cls._normalize_code(target_lang, "google")
            translator = GoogleTranslator(source=g_src, target=g_tgt)
            result = translator.translate(chunk)
            if result:
                return result
        except Exception as e:
            logger.error(f"GoogleTranslator fallback failed: {e}")
        # Final fallback: return original text to avoid 503 errors
        logger.info("All translation providers failed; returning original text.")
        return chunk

    @classmethod
    def translate_pages(
        cls, pages: list[str], source_lang: str, target_lang: str
    ) -> list[str]:
        """
        Translates a list of page texts, preserving page and paragraph boundaries.
        """
        translated_pages: list[str] = []
        cache: dict[str, str] = {}
        for page_text in pages:
            if not page_text.strip():
                translated_pages.append("")
                continue
            chunks = cls._chunk_text(page_text)
            translated_chunks: list[str] = []
            for chunk in chunks:
                if not chunk.strip():
                    translated_chunks.append("")
                    continue
                if chunk in cache:
                    translated_chunks.append(cache[chunk])
                else:
                    translated = cls.translate_chunk(chunk, source_lang, target_lang)
                    cache[chunk] = translated
                    translated_chunks.append(translated)
            translated_pages.append("\n\n".join(translated_chunks))
        return translated_pages
