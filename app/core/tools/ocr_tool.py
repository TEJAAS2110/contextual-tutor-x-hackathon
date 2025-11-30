# app/core/tools/ocr_tool.py
"""
OCR / text extraction tool.

It expects the app to have stored the uploaded bytes in:
- st.session_state["_last_uploaded_pdf_bytes"]  (bytes for PDF)
- OR st.session_state["_last_uploaded_image"]  (bytes for image files)

Returns extracted text (string). If extraction fails, returns an informative message.
"""
from typing import Optional
import streamlit as st

def extract_text_from_session() -> str:
    # PDF bytes -> try PyMuPDF
    if "_last_uploaded_pdf_bytes" in st.session_state:
        try:
            import fitz  # pymupdf
            pdf_bytes = st.session_state["_last_uploaded_pdf_bytes"]
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            text_chunks = []
            # try first 2 pages for speed
            n = min(2, doc.page_count)
            for i in range(n):
                page = doc.load_page(i)
                text_chunks.append(page.get_text().strip())
            out = "\n\n".join([t for t in text_chunks if t.strip()])
            return out if out.strip() else "(no extractable text found in PDF pages)"
        except Exception as e:
            return f"(PDF text extraction failed - install pymupdf or inspect file). Error: {e}"

    # Image bytes -> try PIL + pytesseract
    if "_last_uploaded_image" in st.session_state:
        try:
            from PIL import Image
            from io import BytesIO
            img = Image.open(BytesIO(st.session_state["_last_uploaded_image"]))
            # Try pytesseract if installed
            try:
                import pytesseract
                text = pytesseract.image_to_string(img)
                return text if text.strip() else "(no text found in image via OCR)"
            except Exception as e_ocr:
                return f"(pytesseract not available or OCR failed). Install pytesseract and tesseract-ocr system binary. Error: {e_ocr}"
        except Exception as e_img:
            return f"(Image open failed): {e_img}"

    return "(no uploaded file bytes found in session state)"
