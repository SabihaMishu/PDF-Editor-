import io
import logging
from typing import Optional
import fitz
from PIL import Image
from fastapi import HTTPException, status

from app.utils.text_utils import clean_paragraph_spacing

logger = logging.getLogger(__name__)

# Optional OCR fallback using Windows Native OCR
try:
    # pyrefly: ignore [missing-import]
    import winocr
    HAS_WINOCR = True
except ImportError:
    HAS_WINOCR = False

class PDFExtractorService:
    @staticmethod
    def _run_ocr_on_page(page: fitz.Page, lang: str = "en") -> str:
        """
        Renders a PDF page to a high-DPI image and runs OCR fallback.
        """
        if not HAS_WINOCR:
            logger.warning("OCR requested but winocr is not installed.")
            return ""

        try:
            # Render page at 200 DPI for sharp OCR recognition
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            pil_img = Image.open(io.BytesIO(img_bytes))

            # Match language to available Windows OCR models
            available_tags = [
                l.language_tag.lower()
                for l in winocr.OcrEngine.available_recognizer_languages
            ]
            chosen_tag = "en-US"
            for tag in available_tags:
                if lang.lower() in tag:
                    chosen_tag = tag
                    break

            result = winocr.recognize_pil_sync(pil_img, chosen_tag)
            lines = [
                line["text"].strip()
                for line in result.get("lines", [])
                if line.get("text") and line.get("text").strip()
            ]
            ocr_text = "\n".join(lines) if lines else result.get("text", "").strip()
            if ocr_text:
                logger.info(f"OCR fallback successfully extracted {len(ocr_text)} chars from page {page.number + 1}.")
            return ocr_text
        except Exception as e:
            logger.warning(f"OCR fallback failed on page {page.number + 1}: {e}")
            return ""

    @classmethod
    def extract_text_by_pages(
        cls,
        pdf_bytes: bytes,
        source_lang: str = "en",
        min_chars_for_digital: int = 25
    ) -> list[str]:
        """
        Extracts textual content from PDF bytes page-by-page.
        Applies OCR fallback for scanned or image-heavy pages with missing text.
        Returns a list of cleanly formatted strings (one per page).
        """
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to open PDF document: {str(e)}"
            )

        if doc.page_count == 0:
            doc.close()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The provided PDF document has no pages."
            )

        pages_text: list[str] = []
        total_extracted_chars = 0

        try:
            for page_index in range(doc.page_count):
                page = doc[page_index]

                # 1. Attempt digital text extraction
                raw_text = page.get_text("text").strip()
                has_images = len(page.get_images()) > 0 or len(page.get_drawings()) > 0

                # Check if text is sparse or missing
                needs_ocr = (
                    len(raw_text) < min_chars_for_digital
                    or (has_images and len(raw_text) < 50)
                )

                extracted_text = raw_text
                if needs_ocr:
                    ocr_text = cls._run_ocr_on_page(page, lang=source_lang)
                    # If OCR found more substantial text than raw digital extraction
                    if len(ocr_text.strip()) > len(raw_text.strip()):
                        extracted_text = ocr_text

                # 2. Normalize and clean paragraph spacing
                cleaned_text = clean_paragraph_spacing(extracted_text)
                pages_text.append(cleaned_text)
                total_extracted_chars += len(cleaned_text)
        finally:
            doc.close()

        if total_extracted_chars == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    "No extractable text found in the PDF, even after OCR fallback. "
                    "Please ensure the document contains readable text or clear scans."
                )
            )

        return pages_text
