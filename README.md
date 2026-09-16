# PDF Editor APIs

A robust, high-performance REST API service built with **FastAPI** providing PDF translation, optical character recognition (OCR), text formatting, and document watermarking utilities.

---

## 🚀 Key APIs

### **API A — PDF Language Translator (`POST /api/translate-pdf`)**
- **Completely Free Translation Engine:** Uses **MyMemory** as the primary translator with automatic fallback to **Google public endpoints**.
- **In-Memory Caching:** Automatically caches translated phrases and paragraphs in memory to speed up multi-page documents and avoid duplicate outbound requests.
- **Smart Chunking:** Intelligently splits text into chunks $\le 450$ characters (strictly below MyMemory free limits) respecting paragraphs (`\n\n`), line breaks (`\n`), sentences (`.!?` and Bengali dari `।`), and words.
- **Rate-Limit & Retry Hardening:** Configured with strict 8.0s timeout per request, 0.25s delay between sequential calls, 1.0s backoff, and **max 2 retries** per provider before returning a clean HTTP 503 error.
- **100,000-Character Safety Limit:** Automatically guards backend resources by rejecting documents exceeding 100,000 characters with an HTTP 400 Bad Request.
- **OCR Fallback for Scanned/Image PDFs:** Automatically detects scanned pages or images missing digital text streams and extracts text using native Windows OCR (`winocr`).
- **Clean Text Spacing & De-Hyphenation:** Merges artificial hard line breaks within paragraphs, repairs hyphenated line splits (`trans- \nlated` $\rightarrow$ `translated`), and strips redundant whitespace.
- **Dynamic Page Breaks:** Content flows naturally across pages without creating orphan blank pages.
- **Flawless Bangla OpenType Shaping:** Employs **FPDF2** with **HarfBuzz (`uharfbuzz`)** and embedded **Kalpurush Unicode font**, rendering complex Bengali ligatures (যুক্তাক্ষর: `ক্ষ`, `জ্ঞ`, `ঙ্ক`, `শ্র`) and pre-base vowel diacritics (`ি`, `ে`, `ৈ`) with 100% typographical accuracy.
- **Downloadable Output:** Streams translated vector PDFs directly as downloadable attachments with proper filenames.

---

### **API B — PDF Watermark (`POST /editor/pdf/watermark`)**
- **Full-Document Text Watermarking:** Injects customizable text watermarks across every page of a PDF document.
- **Configurable Watermark Attributes:**
  - `text`: Watermark string (e.g., `CONFIDENTIAL`, `DRAFT`, `COPY`).
  - `position`: Anchor position on each page (`center`, `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, `bottom-right`).
  - `opacity`: Opacity level from `0.0` (invisible) to `1.0` (fully opaque).
  - `color`: Hex color code (e.g., `#FF0000`, `#888888`, `#0055FF`).
- **Vector Overlay Performance:** Fast, zero-quality-loss rendering powered by **PyMuPDF (`fitz`)**.

---

## 🛠️ System Architecture

```
                                  +-------------------+
                                  | Client / Frontend |
                                  +---------+---------+
                                            |
                                            v
                                   +-----------------+
                                   |  FastAPI Router |
                                   +--------+--------+
                                            |
                   +------------------------+------------------------+
                   |                                                 |
                   v                                                 v
        [ POST /api/translate-pdf ]                     [ POST /editor/pdf/watermark ]
                   |                                                 |
         +---------+---------+                             +---------+---------+
         | PDFExtractorService|                             | WatermarkService  |
         | (Digital + WinOCR) |                             | (PyMuPDF Vector)  |
         +---------+---------+                             +---------+---------+
                   |                                                 |
         +---------+---------+                                       v
         |TranslationService |                               [ Watermarked PDF ]
         | - 100k Safety Chk |
         | - In-Memory Cache |
         | - Smart Chunking  |
         | - MyMemory (Pri)  |
         | - Google (Fallbk) |
         | - Max 2 Retries   |
         +---------+---------+
                   |
         +---------+---------+
         | PDFGeneratorService|
         | - FPDF2 + HarfBuzz|
         | - Kalpurush Font  |
         | - Dynamic Breaks  |
         +---------+---------+
                   |
                   v
          [ Translated PDF ]
```

---

## 📦 Setup & Installation

### 1. Prerequisites
- Python 3.10+ (tested on Python 3.11)
- Windows 10/11 (for native OCR engine support)

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Environment Variables (Optional)
Create `.env` if custom port or configuration is required:
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

## 📡 API Reference

### 1. Translate PDF
- **Endpoint:** `POST /api/translate-pdf`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  | Field | Type | Required | Description |
  |---|---|---|---|
  | `file` | Binary (PDF) | Yes | Source PDF file to translate |
  | `source_language` | String | Yes | Source language ISO code (e.g. `en`) |
  | `target_language` | String | Yes | Target language ISO code (e.g. `bn`) |
- **Response:** `200 OK` (binary PDF stream with `attachment` Content-Disposition header).

### 2. Watermark PDF
- **Endpoint:** `POST /editor/pdf/watermark`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  | Field | Type | Required | Description |
  |---|---|---|---|
  | `file` | Binary (PDF) | Yes | Source PDF file |
  | `text` | String | Yes | Watermark text string |
  | `position` | String | Yes | `center`, `top-left`, `top-center`, `top-right`, `bottom-left`, `bottom-center`, `bottom-right` |
  | `opacity` | Float | Yes | `0.0` to `1.0` (e.g. `0.3`) |
  | `color` | String | Yes | Hex color code (e.g. `#FF0000`, `#888888`) |
- **Response:** `200 OK` (binary PDF stream with `attachment` Content-Disposition header).

---

## 🧪 Testing

### Automated Test Suite
Run all unit and integration tests with `pytest`:
```bash
pytest -v
```

The test suite validates:
- [x] Translation endpoint end-to-end PDF output
- [x] 100,000-character safety limit rejection (400 Bad Request)
- [x] Smart chunking & sentence boundary preservation
- [x] In-memory translation caching
- [x] Dual provider fallback (MyMemory $\rightarrow$ Google)
- [x] Max 2 retries & 503 error handling
- [x] OCR extraction on scanned/image-only PDFs
- [x] Dynamic pagination without blank pages
- [x] Watermark PDF positioning, opacity, and color validation
