from fastapi import APIRouter, File, Form, Response, UploadFile
from app.utils.file_utils import validate_pdf_file
from app.services.watermark_service import WatermarkService

router = APIRouter()

@router.post(
    "/editor/pdf/watermark",
    summary="Watermark PDF Document",
    description="Applies a text watermark to every page of a PDF document.",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Returns the newly watermarked PDF document."
        },
        400: {
            "description": "Invalid file format, corrupted PDF structure, or invalid hex color."
        }
    }
)
async def watermark_pdf(
    file: UploadFile = File(..., description="The source PDF file"),
    text: str = Form(..., description="Watermark text, e.g. 'CONFIDENTIAL'"),
    position: str = Form(
        ..., 
        description="Position of the watermark. Options: top-left, top-center, top-right, center, bottom-left, bottom-center, bottom-right"
    ),
    opacity: float = Form(..., ge=0.0, le=1.0, description="Opacity (0.0 to 1.0)"),
    color: str = Form(..., description="Hex color code, e.g. '#FF0000'"),
):
    # 1. Validate uploaded file
    file_bytes = await validate_pdf_file(file)

    # 2. Apply watermark
    watermarked_pdf_bytes = WatermarkService.apply_watermark(
        pdf_bytes=file_bytes,
        text=text,
        position=position,
        opacity=opacity,
        color=color
    )

    # Prepare sanitized filename
    base_name = file.filename.rsplit(".", 1)[0] if file.filename else "document"
    output_filename = f"{base_name}_watermarked.pdf"

    # 3. Return downloadable PDF response
    return Response(
        content=watermarked_pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{output_filename}"'
        }
    )
