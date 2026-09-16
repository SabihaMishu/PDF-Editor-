import fitz
import io
from fastapi import HTTPException, status

class WatermarkService:
    @staticmethod
    def hex_to_rgb(hex_color: str) -> tuple[float, float, float]:
        hex_color = hex_color.lstrip('#')
        if len(hex_color) != 6:
            raise ValueError("Invalid hex color format. Expected format: #RRGGBB")
        return tuple(int(hex_color[i:i+2], 16) / 255.0 for i in (0, 2, 4))

    @classmethod
    def apply_watermark(
        cls, 
        pdf_bytes: bytes, 
        text: str, 
        position: str, 
        opacity: float, 
        color: str
    ) -> bytes:
        try:
            rgb_color = cls.hex_to_rgb(color)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
            
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or corrupted PDF file.")

        for page in doc:
            rect = page.rect
            margin = 36
            width = rect.width
            height = rect.height
            
            fontsize = 48
            text_length = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
            
            # Dynamically scale font down if text is too wide for the page
            if text_length > width - 2*margin:
                fontsize = max(10, fontsize * (width - 2*margin) / text_length)
                text_length = fitz.get_text_length(text, fontname="helv", fontsize=fontsize)
                
            x_center = width / 2
            y_center = height / 2
            
            if position == "top-left":
                p = fitz.Point(margin, margin + fontsize)
            elif position == "top-center":
                p = fitz.Point(x_center - text_length/2, margin + fontsize)
            elif position == "top-right":
                p = fitz.Point(width - margin - text_length, margin + fontsize)
            elif position == "center":
                p = fitz.Point(x_center - text_length/2, y_center + fontsize/2)
            elif position == "bottom-left":
                p = fitz.Point(margin, height - margin)
            elif position == "bottom-center":
                p = fitz.Point(x_center - text_length/2, height - margin)
            elif position == "bottom-right":
                p = fitz.Point(width - margin - text_length, height - margin)
            else:
                # Default to center if unknown
                p = fitz.Point(x_center - text_length/2, y_center + fontsize/2)
                
            page.insert_text(p, text, fontname="helv", fontsize=fontsize, color=rgb_color, fill_opacity=opacity)
            
        pdf_out = doc.write()
        doc.close()
        return pdf_out
