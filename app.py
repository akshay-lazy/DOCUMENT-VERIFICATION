import hashlib
import io
import json
import re
from datetime import datetime

import streamlit as st

st.set_page_config(page_title="VeriAI | Document Validation", page_icon="🛡️", layout="wide")

st.markdown("""
<style>
.block-container {padding-top: 1.5rem; max-width: 1200px;}
.hero {padding: 1.5rem; border-radius: 18px; background: linear-gradient(120deg,#102a43,#176b87); color: white;}
.hero h1, .hero h3, .hero p {color: white;}
div[data-testid="stMetric"] {background: rgba(100,120,140,.08); padding: 12px; border-radius: 12px;}
</style>
""", unsafe_allow_html=True)

st.markdown(
    '<div class="hero"><h1>🛡️ VeriAI</h1>'
    '<h3>AI-Powered Document Authentication & Compliance</h3>'
    '<p>Prototype • OCR diagnostics • Field validation • Image-quality checks • Audit hash</p></div>',
    unsafe_allow_html=True,
)
st.write("")
st.warning(
    "DEMO ONLY: VeriAI does not prove that a document is genuine and is not connected to UIDAI, "
    "DigiLocker, banks, or government registries. Use fictional/sample documents only. "
    "Do not upload real Aadhaar, identity, banking, or other sensitive documents."
)

SUPPORTED_IMAGES = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff")
SUPPORTED_FILES = [".txt", ".pdf", ".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"]

def sha256_bytes(data):
    return hashlib.sha256(data).hexdigest()

def detect_document_hint(text):
    """Simple keyword hint, not a trained AI classifier."""
    t = text.lower()
    if any(k in t for k in ["aadhaar", "uidai", "government of india", "unique identification"]):
        return "May resemble an Aadhaar-style document (keyword match only)"
    if any(k in t for k in ["marksheet", "transcript", "university", "certificate", "registration no"]):
        return "May resemble a certificate or academic document (keyword match only)"
    if any(k in t for k in ["invoice", "gstin", "total amount", "tax invoice", "balance sheet"]):
        return "May resemble a financial document (keyword match only)"
    if t.strip():
        return "Document type not confidently inferred from extracted text"
    return "Unable to infer document type because no text was extracted"

def ocr_image(image):
    """Return extracted text and a clear status message."""
    try:
        from PIL import Image, ImageOps, ImageEnhance, ImageFilter
    except Exception as exc:
        return "", f"Pillow is unavailable: {exc}. Run: python -m pip install Pillow"

    try:
        import pytesseract
    except Exception as exc:
        return "", f"Python OCR package is unavailable: {exc}. Run: python -m pip install pytesseract"

    try:
        # Convert to RGB, correct EXIF orientation, and slightly improve contrast.
        image = ImageOps.exif_transpose(image).convert("RGB")
        image = ImageEnhance.Contrast(image).enhance(1.25)
        text = pytesseract.image_to_string(image)
        if text.strip():
            return text.strip(), "OCR completed using Tesseract"
        return "", "OCR ran, but no readable text was detected. Try a clearer, straight, well-lit sample image."
    except pytesseract.pytesseract.TesseractNotFoundError:
        return "", (
            "Tesseract OCR engine is not installed or was not found. On macOS, install it with "
            "`brew install tesseract`, then restart the terminal and Streamlit."
        )
    except Exception as exc:
        return "", f"OCR failed: {type(exc).__name__}: {exc}"

def extract_text(filename, data):
    name = filename.lower()
    if name.endswith(".txt"):
        try:
            return data.decode("utf-8", errors="replace"), "Text file read successfully"
        except Exception as exc:
            return "", f"Could not read text file: {exc}"

    if name.endswith(".pdf"):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(data))
            page_texts = []
            for page in reader.pages:
                page_texts.append(page.extract_text() or "")
            text = "\n".join(page_texts).strip()
            if text:
                return text, f"PDF text extraction completed ({len(reader.pages)} page(s))"
            return "", (
                f"PDF opened ({len(reader.pages)} page(s)), but no selectable text was found. "
                "This may be a scanned PDF. For this prototype, try uploading a page as an image "
                "or use a text-based PDF."
            )
        except Exception as exc:
            return "", f"PDF processing failed: {type(exc).__name__}: {exc}"

    if name.endswith(SUPPORTED_IMAGES):
        try:
            from PIL import Image
            image = Image.open(io.BytesIO(data))
            return ocr_image(image)
        except Exception as exc:
            return "", f"Image could not be opened: {type(exc).__name__}: {exc}"

    return "", "Unsupported file type. Upload TXT, PDF, PNG, JPG, BMP, TIF, or TIFF."

def field_check(text, document_type):
    fields_by_type = {
        "Identity-style sample": ["name", "date of birth", "address"],
        "Certificate": ["name", "institution", "date"],
        "Financial document": ["name", "date", "total amount"],
        "General document": ["name", "date"],
    }
    required = fields_by_type[document_type]
    lower = text.lower()
    variants = {
        "date of birth": ["date of birth", "dob", "birth date"],
        "institution": ["institution", "school", "college", "university"],
        "total amount": ["total amount", "grand total", "amount due", "total"],
    }
    results = []
    for field in required:
        found = any(v in lower for v in variants.get(field, [field]))
        results.append({"field": field.title(), "status": "Label detected" if found else "Label not detected"})
    return results

def image_quality_checks(filename, data):
    if not filename.lower().endswith(SUPPORTED_IMAGES):
        return ["Skipped: basic image-quality checks only run on image files."]
    try:
        from PIL import Image
        import numpy as np
        import cv2
        image = Image.open(io.BytesIO(data)).convert("RGB")
        arr = np.array(image)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
        height, width = gray.shape
        blur_score = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        notes = [
            f"Image dimensions: {width} × {height} pixels.",
            f"Sharpness indicator (Laplacian variance): {blur_score:.1f}.",
            "These are image-quality indicators only; they do not detect or prove forgery.",
        ]
        if width < 500 or height < 300:
            notes.append("The image is relatively small; text extraction may be unreliable.")
        if blur_score < 40:
            notes.append("The image may be blurry. Try a sharper sample image.")
        return notes
    except Exception as exc:
        return [f"Image-quality checks could not run: {type(exc).__name__}: {exc}"]

with st.sidebar:
    st.header("Validation settings")
    doc_type = st.selectbox(
        "Document category",
        ["Identity-style sample", "Certificate", "Financial document", "General document"],
    )
    st.caption("This category controls the required-field checklist. It does not authenticate the document.")
    st.divider()
    st.caption("Keyword-based document hints are experimental and are not a trained AI classifier.")
    st.caption("No external verification API is connected.")

uploaded = st.file_uploader(
    "Upload a fictional sample document",
    type=["txt", "pdf", "png", "jpg", "jpeg", "bmp", "tif", "tiff"],
    help="Use fictional test data only. Maximum size is controlled by Streamlit's configuration.",
)

if uploaded is not None:
    data = uploaded.getvalue()
    file_hash = sha256_bytes(data)

    st.subheader("1. Upload status")
    c1, c2, c3 = st.columns(3)
    c1.metric("File", uploaded.name)
    c2.metric("Size", f"{len(data) / 1024:.1f} KB")
    c3.metric("SHA-256", file_hash[:16] + "…")
    st.caption("A SHA-256 hash helps identify exact file changes; it does not establish authenticity.")

    if uploaded.name.lower().endswith(SUPPORTED_IMAGES):
        try:
            from PIL import Image
            preview = Image.open(io.BytesIO(data))
            st.image(preview, caption="Uploaded image preview", use_container_width=True)
        except Exception as exc:
            st.error(f"The file was selected, but the image preview failed: {type(exc).__name__}: {exc}")

    with st.spinner("Processing your sample document…"):
        extracted, extraction_status = extract_text(uploaded.name, data)

    st.subheader("2. Text extraction")
    st.write(f"**Status:** {extraction_status}")
    if extracted.strip():
        st.text_area("Extracted text", value=extracted, height=200)
        st.info("Text extraction reads visible text; it does not check whether the values are true.")
    else:
        st.warning("No text was extracted. See the status above for the likely cause.")
        with st.expander("Image/PDF troubleshooting"):
            st.markdown(
                "- For images, confirm that Tesseract is installed: `tesseract --version`.\n"
                "- If the command is missing on macOS, install Homebrew if needed, then run `brew install tesseract`.\n"
                "- Restart the terminal and restart Streamlit after installation.\n"
                "- Try a clear, straight, high-resolution sample image.\n"
                "- A scanned PDF may need OCR; try a single page exported as PNG/JPG for this prototype."
            )

    st.subheader("3. Document-type hint")
    st.write(detect_document_hint(extracted))
    st.caption("This is a simple keyword hint, not reliable identity recognition.")

    st.subheader("4. Required-field checks")
    checks = field_check(extracted, doc_type)
    for item in checks:
        if item["status"] == "Label detected":
            st.success(f'{item["field"]}: {item["status"]}')
        else:
            st.warning(f'{item["field"]}: {item["status"]}')

    st.subheader("5. Basic image-quality checks")
    for note in image_quality_checks(uploaded.name, data):
        st.write("• " + note)

    missing = [item["field"] for item in checks if item["status"] != "Label detected"]
    st.subheader("6. Review summary")
    left, right = st.columns(2)
    with left:
        if missing:
            st.warning("Field labels needing review: " + ", ".join(missing))
        else:
            st.success("All configured field labels were detected.")
    with right:
        st.warning("Authenticity: NOT VERIFIED")
        st.caption("No trusted issuer or government registry is connected.")

    report = {
        "project": "VeriAI prototype",
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "file_name": uploaded.name,
        "file_size_bytes": len(data),
        "sha256": file_hash,
        "document_category": doc_type,
        "extraction_status": extraction_status,
        "document_type_hint": detect_document_hint(extracted),
        "extracted_text": extracted,
        "required_fields": checks,
        "fields_needing_review": missing,
        "authenticity_status": "NOT VERIFIED",
        "limitations": [
            "No trusted issuer or government registry connected",
            "Keyword hints are not a trained document classifier",
            "OCR may misread or miss text",
            "Image-quality checks are not forgery detection",
            "Human review is required for consequential decisions",
        ],
    }
    st.subheader("7. Download report")
    st.download_button(
        "Download JSON validation report",
        data=json.dumps(report, indent=2, ensure_ascii=False),
        file_name="veriai_validation_report.json",
        mime="application/json",
    )
else:
    st.markdown("### How to test")
    st.write("1. Upload `sample_document.txt` or a fictional sample image.")
    st.write("2. Choose the closest category in the sidebar.")
    st.write("3. Review the extraction status and report.")
    st.caption("If an image fails, the app now shows a specific OCR error instead of silently hiding the cause.")
