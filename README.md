# PDF Editor APIs

A robust, high-performance REST API service built with **FastAPI** providing PDF editing, translation, and transformation utilities.

---

## 🚀 Features

### **API A — PDF Language Translator (`POST /api/translate-pdf`)**
- **Multilingual Support:** Translates between supported languages (e.g., English `en` to Bangla `bn`).
- **OCR Fallback for Image/Scanned PDFs:** Automatically identifies image-only or scanned pages with missing digital text streams and runs native OCR fallback (`winocr`) to extract text.
- **Clean Text Spacing & De-Hyphenation:** Merges artificial hard line breaks within paragraphs into smooth, flowing prose; repairs hyphenated line splits (`trans- \nlated` $\rightarrow$ `translated`); and eliminates redundant spaces.
- **Dynamic Page Breaks & Blank Page Prevention:** Content flows naturally across pages without generating empty or trailing blank pages. Dynamically assesses vertical page space before creating new pages or section dividers.
- **Flawless Bangla OpenType Shaping:** Utilizes **FPDF2** paired with **HarfBuzz (`uharfbuzz`)** and embedded **Kalpurush Unicode font**, rendering complex Bengali ligatures (যুক্তাক্ষর: `ক্ষ`, `জ্ঞ`, `ঙ্ক`, `শ্র`) and pre-base vowel signs (`ি`, `ে`, `ৈ`) with 100% typographical accuracy.
- **Downloadable Output:** Streams freshly generated vector PDFs as downloadable attachments with proper filenames.
- **Interactive OpenAPI / Swagger UI:** Available out-of-the-box at `/docs`.

---

## 🛠️ Architecture & Technical Design

### 1. Optical Character Recognition (OCR) Fallback
When processing documents containing scanned paper, raster graphics, or flattened text, standard digital extraction produces empty strings. 
- The extractor checks if extracted digital text is below threshold (`< 25` characters or image-dominated).
- If triggered, the page is rendered to a crisp 200-DPI raster in memory and processed by native Windows OCR (`winocr`).
- If OCR yields text, it seamlessly replaces the empty digital layer.

### 2. Dynamic Page Breaks & Clean Spacing
Older PDF generators often call `pdf.add_page()` blindly for each source page, creating orphan blank pages when source pages have minimal or no content.
- Our generator checks vertical position `pdf.get_y()`. If remaining page height is ample ($\ge 45\,\text{mm}$), it separates content with clean section gaps.
- When space is insufficient ($< 45\,\text{mm}$), it dynamically triggers a clean page break.
- Auto-page breaks during paragraph wrapping are respected without inserting duplicate blank pages.

### 3. Bangla Unicode Text Shaping
- Standard PDF libraries (and raw PyMuPDF text insertion) fail on Indic scripts because glyphs must undergo GSUB (Glyph Substitution) and GPOS (Glyph Positioning).
- By enabling `pdf.set_text_shaping(True)` in `fpdf2`, `uharfbuzz` shapes complex ligatures and reorders vowel diacritics before the vector stream is written.
- Embedded `Kalpurush.ttf` font supports both full Latin and Bengali Unicode blocks.

---

## 📦 Setup & Installation

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11)
- Windows 10/11 (with Windows Media OCR support)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables (Optional)
Copy `.env.example` to `.env` if custom configurations are needed:
```bash
cp .env.example .env
```

---

## 🏃 Running the Server

Start the FastAPI application with Uvicorn:
```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Once running:
- **Interactive Swagger UI:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check:** [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🧪 Testing

### Automated Test Suite
Run the test suite with `pytest`:
```bash
pytest -v
```
*(Tests verify digital extraction, OCR fallback on scanned images, text normalization, dynamic pagination with zero blank pages, and endpoint responses).*

### Manual Testing via Swagger UI (`/docs`)
1. Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
2. Expand `POST /api/translate-pdf` and click **Try it out**.
3. Upload a PDF file (digital or scanned).
4. Set `source_language`: `en`, `target_language`: `bn`.
5. Click **Execute** and click **Download file** from the response.

### Manual Testing via Postman
1. Import [postman_collection.json](file:///D:/mishu/Projects/PDF%20Editor/postman_collection.json) into Postman.
2. Run `API A - Translate PDF (EN to BN)`.
