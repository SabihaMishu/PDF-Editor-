import io
from fastapi import APIRouter, File, Form, HTTPException, Response, UploadFile, status
from app.utils.file_utils import validate_pdf_file
from app.services.pdf_extractor import PDFExtractorService
from app.services.translation_service import TranslationService
from app.services.pdf_generator import PDFGeneratorService

router = APIRouter()

@router.post(
    "/translate-pdf",
    summary="Translate PDF Document",
    description=(
        "Upload a PDF file and specify source and target languages. "
        "Extracts digital text with automatic OCR fallback for scanned/image pages, "
        "translates content with sentence boundary preservation, and generates a clean, "
        "dynamically paginated PDF with full Bangla Unicode shaping."
    ),
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns the newly generated, translated PDF document."
        },
        400: {
            "description": "Invalid file format or corrupted PDF structure."
        },
        422: {
            "description": "PDF contains no extractable text, even after OCR fallback."
        },
        503: {
            "description": "Translation engine temporarily unavailable."
        }
    }
)
async def translate_pdf(
    file: UploadFile = File(..., description="The source PDF file to translate"),
    source_language: str = Form(
        ...,
        description="Source language code (e.g., 'en' for English, 'bn' for Bangla)",
        examples=["en"]
    ),
    target_language: str = Form(
        ...,
        description="Target language code (e.g., 'bn' for Bangla, 'en' for English)",
        examples=["bn"]
    ),
):
    # 1. Validate uploaded file
    file_bytes = await validate_pdf_file(file)

    # 2. Extract text page-by-page (with OCR fallback for image/scanned pages)
    pages_text = PDFExtractorService.extract_text_by_pages(
        pdf_bytes=file_bytes,
        source_lang=source_language
    )

    # 3. Translate extracted text preserving page boundaries
    translated_pages = TranslationService.translate_pages(
        pages=pages_text,
        source_lang=source_language,
        target_lang=target_language
    )

    # 4. Generate new PDF document with dynamic page breaks and Bangla text shaping
    translated_pdf_bytes = PDFGeneratorService.generate_pdf(translated_pages)

    # Prepare sanitized filename
    base_name = file.filename.rsplit(".", 1)[0] if file.filename else "document"
    output_filename = f"{base_name}_translated_{target_language.lower()}.pdf"

    # 5. Return downloadable PDF response
    return Response(
        content=translated_pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"'
        }
    )
