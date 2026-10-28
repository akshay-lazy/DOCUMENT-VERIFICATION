# VeriAI — improved beginner prototype

## What this version improves
- Shows an image preview after upload.
- Gives clearer OCR errors, including when the Tesseract engine is missing.
- Adds simple keyword-based document-type hints.
- Supports TXT, PDF, PNG, JPG, BMP, TIF and TIFF uploads.
- Adds a clearer review summary and JSON report.
- Keeps authenticity status explicitly `NOT VERIFIED`.

## Important limitation
This is a learning prototype. It does not verify genuine documents, connect to UIDAI/DigiLocker/government systems, or reliably detect forged documents. Keyword hints are not a trained AI model. Use fictional test files only.

## Run on macOS
Open this folder in VS Code, then open Terminal in VS Code and run:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL printed by Streamlit, usually `http://localhost:8501`.

## OCR engine on macOS
The Python package `pytesseract` is only a bridge; the Tesseract program must also be installed. If Homebrew is installed:

```bash
brew install tesseract
tesseract --version
```

Then restart Streamlit. If you do not have Homebrew or the installation fails, share the terminal error before proceeding.

## Test
Upload `sample_document.txt` first. Then try a clear, fictional JPG or PNG. Check the extraction status shown on the page and in the VS Code terminal.

## Privacy
Do not upload real Aadhaar, identity, financial, or other sensitive documents.
