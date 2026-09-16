import os
from pathlib import Path
from fpdf import FPDF
from app.core.config import settings
from app.utils.text_utils import clean_paragraph_spacing

class DocumentPDF(FPDF):
    """Custom FPDF subclass with page numbering."""
    def footer(self):
        self.set_y(-15)
        self.set_font("DocumentFont", size=9)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f"Page {self.page_no()}", align="C")

class PDFGeneratorService:
    @staticmethod
    def _resolve_font() -> str:
        """Finds available Unicode font supporting Bangla."""
        if os.path.exists(settings.BANGLA_FONT_PATH):
            return str(settings.BANGLA_FONT_PATH)
        if os.path.exists(settings.NOTO_FONT_PATH):
            return str(settings.NOTO_FONT_PATH)
        raise FileNotFoundError(
            f"No suitable Unicode font found at {settings.BANGLA_FONT_PATH} or {settings.NOTO_FONT_PATH}"
        )

    @classmethod
    def generate_pdf(cls, pages_text: list[str]) -> bytes:
        """
        Builds a fresh, cleanly formatted PDF containing the translated text.
        Features:
        - Dynamic page breaks (avoids unnecessary blank pages).
        - Clean paragraph spacing and de-hyphenation.
        - OpenType text shaping with embedded Kalpurush font (100% Bangla ligature fidelity).
        """
        font_path = cls._resolve_font()

        pdf = DocumentPDF(orientation="P", unit="mm", format="A4")
        pdf.set_margins(left=20, top=20, right=20)
        # Margin bottom = 20mm with auto page break enabled
        pdf.set_auto_page_break(auto=True, margin=20)

        # Register embedded Unicode font
        pdf.add_font("DocumentFont", "", font_path)
        pdf.set_font("DocumentFont", size=11)
        pdf.set_text_shaping(True)
        pdf.set_text_color(33, 37, 41)

        # 1. Filter out empty or whitespace-only pages to eliminate blank pages
        cleaned_pages: list[str] = []
        for p in pages_text:
            cleaned = clean_paragraph_spacing(p)
            if cleaned.strip():
                cleaned_pages.append(cleaned.strip())

        # Fallback if no content exists
        if not cleaned_pages:
            pdf.add_page()
            pdf.multi_cell(w=0, h=8, text="No translated text available.")
            return bytes(pdf.output())

        # Start initial page
        pdf.add_page()

        page_height = pdf.h           # 297 mm for A4
        bottom_margin = pdf.b_margin  # 20 mm
        top_margin = pdf.t_margin     # 20 mm
        usable_bottom = page_height - bottom_margin

        for doc_idx, page_content in enumerate(cleaned_pages):
            # Dynamic section break: only add a page break if previous page has substantial content
            # and there is insufficient space (< 45 mm) to render the next section cleanly
            if doc_idx > 0:
                current_y = pdf.get_y()
                remaining_space = usable_bottom - current_y

                if remaining_space < 45:
                    # If we are not already at the top of a page
                    if current_y > top_margin + 5:
                        pdf.add_page()
                else:
                    # Ample space: add a clean section separator gap
                    pdf.ln(5)

            # Output paragraphs with clean typography
            paragraphs = page_content.split("\n\n")
            for para_idx, para in enumerate(paragraphs):
                para = para.strip()
                if not para:
                    continue

                # Multi_cell handles automatic word-wrapping and HarfBuzz text shaping
                try:
                    pdf.multi_cell(w=0, h=6.5, text=para)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"multi_cell exception: {e}. Falling back to character-level wrapping.")
                    pdf.multi_cell(w=0, h=6.5, text=para, wrapmode="CHAR")

                # Paragraph spacing (only if there's enough space left on page)
                if para_idx < len(paragraphs) - 1:
                    remaining = usable_bottom - pdf.get_y()
                    if remaining > 10:
                        pdf.ln(3.5)

        return bytes(pdf.output())
