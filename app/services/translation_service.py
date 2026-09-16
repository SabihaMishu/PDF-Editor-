import re
import time
import logging
import requests
from typing import Optional
from fastapi import HTTPException, status

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
    # In-memory translation cache: (source_lang, target_lang, text) -> translated_text
    _cache: dict[tuple[str, str, str], str] = {}
    
    # Constants
    MAX_CHAR_SAFETY_LIMIT = 100_000
    MAX_CHUNK_SIZE = 450  # Safe for MyMemory free tier (limit ~500 chars)
    MAX_RETRIES = 2
    TIMEOUT_SECONDS = 8.0
    REQUEST_DELAY_SECONDS = 0.25
    RETRY_DELAY_SECONDS = 1.0

    @classmethod
    def clear_cache(cls) -> None:
        """Clears the in-memory translation cache."""
        cls._cache.clear()

    @classmethod
    def get_cache_size(cls) -> int:
        """Returns the number of cached items."""
        return len(cls._cache)

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
    def _chunk_text(cls, text: str, max_chunk_size: int = MAX_CHUNK_SIZE) -> list[str]:
        """
        Splits text into chunks <= max_chunk_size characters,
        prioritizing double newlines, then single newlines, then sentences (including Bengali ।).
        """
        if not text:
            return []
            
        paragraphs = text.split("\n\n")
        chunks: list[str] = []
        current_chunk = ""
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            
            if len(current_chunk) + len(para) + 2 <= max_chunk_size:
                current_chunk = f"{current_chunk}\n\n{para}".strip() if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                if len(para) <= max_chunk_size:
                    current_chunk = para
                else:
                    # Split on line breaks first
                    lines = para.split("\n")
                    for line in lines:
                        line = line.strip()
                        if not line:
                            continue
                        if len(current_chunk) + len(line) + 1 <= max_chunk_size:
                            current_chunk = f"{current_chunk}\n{line}".strip() if current_chunk else line
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                                current_chunk = ""
                            
                            if len(line) <= max_chunk_size:
                                current_chunk = line
                            else:
                                # Split by sentence punctuation (.!? and Bengali dari ।)
                                sentences = re.split(r"(?<=[.!?|।])\s+", line)
                                for sent in sentences:
                                    sent = sent.strip()
                                    if not sent:
                                        continue
                                    if len(current_chunk) + len(sent) + 1 <= max_chunk_size:
                                        current_chunk = f"{current_chunk} {sent}".strip() if current_chunk else sent
                                    else:
                                        if current_chunk:
                                            chunks.append(current_chunk)
                                            current_chunk = ""
                                        
                                        if len(sent) <= max_chunk_size:
                                            current_chunk = sent
                                        else:
                                            # Fallback: split long unbroken string on words/spaces
                                            words = sent.split(" ")
                                            for word in words:
                                                if len(current_chunk) + len(word) + 1 <= max_chunk_size:
                                                    current_chunk = f"{current_chunk} {word}".strip() if current_chunk else word
                                                else:
                                                    if current_chunk:
                                                        chunks.append(current_chunk)
                                                    current_chunk = word
        
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    @classmethod
    def _translate_mymemory(cls, text: str, source_lang: str, target_lang: str) -> str:
        """Translates text using MyMemory public API endpoint with strict timeout."""
        src = cls._normalize_code(source_lang, "mymemory")
        tgt = cls._normalize_code(target_lang, "mymemory")
        
        url = "https://api.mymemory.translated.net/get"
        params = {
            "q": text,
            "langpair": f"{src}|{tgt}"
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PDF-Editor/1.0"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=cls.TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        
        # Check MyMemory response status code and quota warnings
        if data.get("responseStatus") != 200:
            raise RuntimeError(f"MyMemory error: {data.get('responseDetails')}")
            
        translated = data.get("responseData", {}).get("translatedText", "")
        if not translated:
            raise RuntimeError("MyMemory returned empty translation")
            
        if "MYMEMORY WARNING" in translated.upper():
            raise RuntimeError(f"MyMemory quota limit: {translated}")
            
        return translated

    @classmethod
    def _translate_google(cls, text: str, source_lang: str, target_lang: str) -> str:
        """Translates text using Google public web API endpoint with strict timeout."""
        src = cls._normalize_code(source_lang, "google")
        tgt = cls._normalize_code(target_lang, "google")
        
        url = "https://translate.googleapis.com/translate_a/single"
        params = {
            "client": "gtx",
            "sl": src,
            "tl": tgt,
            "dt": "t",
            "q": text
        }
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=cls.TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        
        if not data or not isinstance(data, list) or not data[0]:
            raise RuntimeError("Google translate returned unexpected structure")
            
        translated_parts = [segment[0] for segment in data[0] if segment and len(segment) > 0 and segment[0]]
        translated = "".join(translated_parts)
        if not translated:
            raise RuntimeError("Google translate returned empty string")
            
        return translated

    @classmethod
    def translate_batch(cls, text_chunk: str, source_lang: str, target_lang: str) -> str:
        """
        Translates a chunk of text:
        - Checks in-memory cache first
        - Tries MyMemory (up to 2 attempts with timeout & retry delay)
        - Falls back to Google public endpoint (up to 2 attempts with timeout & retry delay)
        - Applies request delay between outbound requests
        - Caches successful translation
        - Raises 503 if both providers fail
        """
        if not text_chunk or not text_chunk.strip():
            return text_chunk
            
        src_clean = source_lang.strip().lower()
        tgt_clean = target_lang.strip().lower()
        if src_clean == tgt_clean:
            return text_chunk

        # Check Cache
        cache_key = (src_clean, tgt_clean, text_chunk)
        if cache_key in cls._cache:
            return cls._cache[cache_key]

        # Primary: MyMemory (Max 2 attempts)
        for attempt in range(1, cls.MAX_RETRIES + 1):
            try:
                translated = cls._translate_mymemory(text_chunk, source_lang, target_lang)
                if translated:
                    cls._cache[cache_key] = translated
                    time.sleep(cls.REQUEST_DELAY_SECONDS)
                    return translated
            except Exception as e:
                logger.warning(f"MyMemory attempt {attempt}/{cls.MAX_RETRIES} failed: {e}")
                if attempt < cls.MAX_RETRIES:
                    time.sleep(cls.RETRY_DELAY_SECONDS)

        logger.info("MyMemory unavailable after retries. Falling back to Google public endpoint...")

        # Fallback: Google Public Endpoint (Max 2 attempts)
        for attempt in range(1, cls.MAX_RETRIES + 1):
            try:
                translated = cls._translate_google(text_chunk, source_lang, target_lang)
                if translated:
                    cls._cache[cache_key] = translated
                    time.sleep(cls.REQUEST_DELAY_SECONDS)
                    return translated
            except Exception as e:
                logger.warning(f"Google fallback attempt {attempt}/{cls.MAX_RETRIES} failed: {e}")
                if attempt < cls.MAX_RETRIES:
                    time.sleep(cls.RETRY_DELAY_SECONDS)

        # Both providers exhausted
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Translation providers (MyMemory & Google) are temporarily unavailable or rate-limited. Please try again shortly."
        )

    @classmethod
    def translate_pages(
        cls, pages: list[str], source_lang: str, target_lang: str
    ) -> list[str]:
        """
        Validates safety character limit and translates a list of page texts
        using smart chunking, caching, request delays, and fallback mechanism.
        """
        # Safety limit check (100,000 characters)
        total_chars = sum(len(p) for p in pages)
        if total_chars > cls.MAX_CHAR_SAFETY_LIMIT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"PDF text length ({total_chars} characters) exceeds the safety limit of {cls.MAX_CHAR_SAFETY_LIMIT} characters."
            )

        translated_pages: list[str] = []
        
        for page_text in pages:
            if not page_text or not page_text.strip():
                translated_pages.append("")
                continue
                
            chunks = cls._chunk_text(page_text, max_chunk_size=cls.MAX_CHUNK_SIZE)
            translated_chunks: list[str] = []
            
            for chunk in chunks:
                if not chunk.strip():
                    translated_chunks.append("")
                    continue
                translated = cls.translate_batch(chunk, source_lang, target_lang)
                translated_chunks.append(translated)
                    
            translated_pages.append("\n\n".join(translated_chunks))
            
        return translated_pages
