import io
import fitz
from PIL import Image, ImageDraw
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.services.pdf_extractor import PDFExtractorService
from app.services.pdf_generator import PDFGeneratorService
from app.utils.text_utils import clean_paragraph_spacing

client = TestClient(app)

def create_sample_pdf(text: str = "Hello World! Welcome to the PDF translation test.") -> bytes:
    """Helper to create a small in-memory valid digital PDF document."""
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 72), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def create_scanned_image_pdf(text: str = "OCR Test Invoice #1024") -> bytes:
    """Helper to create a PDF containing an image of text (no digital text stream)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    img = Image.new("RGB", (600, 150), color="white")
    d = ImageDraw.Draw(img)
    d.text((20, 50), text, fill="black")

    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_bytes = img_buffer.getvalue()

    rect = fitz.Rect(50, 100, 545, 250)
    page.insert_image(rect, stream=img_bytes)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "PDF Editor API"}

def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "online"
    assert "/docs" in response.json()["documentation"]

def test_invalid_file_extension():
    response = client.post(
        "/api/translate-pdf",
        files={"file": ("test.txt", b"plain text", "text/plain")},
        data={"source_language": "en", "target_language": "bn"}
    )
    assert response.status_code == 400
    assert "Only PDF files are supported" in response.json()["detail"]

def test_corrupted_or_non_pdf_content():
    response = client.post(
        "/api/translate-pdf",
        files={"file": ("test.pdf", b"not a real pdf content", "application/pdf")},
        data={"source_language": "en", "target_language": "bn"}
    )
    assert response.status_code == 400
    assert "Invalid PDF structure" in response.json()["detail"]

def test_empty_file():
    response = client.post(
        "/api/translate-pdf",
        files={"file": ("empty.pdf", b"", "application/pdf")},
        data={"source_language": "en", "target_language": "bn"}
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()

def test_clean_paragraph_spacing():
    raw_sample = (
        "This is an arti- \nficially broken line that\nshould be merged.\n\n"
        "Second paragraph with   extra   spaces."
    )
    cleaned = clean_paragraph_spacing(raw_sample)
    assert "artificially broken line that should be merged." in cleaned
    assert "Second paragraph with extra spaces." in cleaned
    assert "\n\n" in cleaned

def test_pdf_extractor_service_digital_text():
    sample_bytes = create_sample_pdf("Testing PDF Extractor Service.")
    pages = PDFExtractorService.extract_text_by_pages(sample_bytes)
    assert len(pages) == 1
    assert "Testing PDF Extractor Service" in pages[0]

def test_pdf_extractor_service_ocr_fallback():
    scanned_bytes = create_scanned_image_pdf("Scanned OCR Test Line")
    pages = PDFExtractorService.extract_text_by_pages(scanned_bytes, source_lang="en")
    assert len(pages) == 1
    # Check that OCR recovered text from the image
    assert len(pages[0].strip()) > 0

def test_dynamic_page_breaks_no_blank_pages():
    # 3 small text fragments and empty pages should condense without empty pages
    input_pages = [
        "Short note 1.",
        "",
        "   ",
        "Short note 2."
    ]
    output_pdf = PDFGeneratorService.generate_pdf(input_pages)
    doc = fitz.open(stream=output_pdf, filetype="pdf")
    # All short notes fit comfortably on a single dynamic page
    assert doc.page_count == 1
    doc.close()

def test_translate_pdf_endpoint_success():
    sample_bytes = create_sample_pdf("Hello world! This is an automated test.")
    
    with patch(
        "app.services.translation_service.TranslationService.translate_chunk",
        return_value="হ্যালো বিশ্ব! এটি একটি স্বয়ংক্রিয় পরীক্ষা।"
    ):
        response = client.post(
            "/api/translate-pdf",
            files={"file": ("sample.pdf", sample_bytes, "application/pdf")},
            data={"source_language": "en", "target_language": "bn"}
        )
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "translated_bn.pdf" in response.headers.get("content-disposition", "")
        assert response.content.startswith(b"%PDF-")

        # Verify generated PDF parses cleanly
        doc = fitz.open(stream=response.content, filetype="pdf")
        assert doc.page_count == 1
        doc.close()
