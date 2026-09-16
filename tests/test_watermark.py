from fastapi.testclient import TestClient
import io
import fitz
from app.main import app
from tests.test_translate import create_sample_pdf

client = TestClient(app)

def test_watermark_pdf_endpoint_success():
    sample_bytes = create_sample_pdf("This is a test PDF for watermarking.")
    
    response = client.post(
        "/editor/pdf/watermark",
        files={"file": ("sample.pdf", sample_bytes, "application/pdf")},
        data={
            "text": "CONFIDENTIAL",
            "position": "center",
            "opacity": 0.5,
            "color": "#FF0000"
        }
    )
    
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "sample_watermarked.pdf" in response.headers.get("content-disposition", "")
    assert response.content.startswith(b"%PDF-")
    
    # Verify the watermark is applied by checking if text is present
    doc = fitz.open(stream=response.content, filetype="pdf")
    page = doc[0]
    extracted = page.get_text()
    assert "CONFIDENTIAL" in extracted
    doc.close()

def test_watermark_pdf_endpoint_invalid_color():
    sample_bytes = create_sample_pdf("This is a test PDF for watermarking.")
    
    response = client.post(
        "/editor/pdf/watermark",
        files={"file": ("sample.pdf", sample_bytes, "application/pdf")},
        data={
            "text": "CONFIDENTIAL",
            "position": "center",
            "opacity": 0.5,
            "color": "red"  # Invalid format
        }
    )
    
    assert response.status_code == 400
    assert "Invalid hex color format" in response.json()["detail"]
