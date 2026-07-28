"""
Step 1 of the RAG pipeline: break documents into smaller sections for processing.

- extract_pages(): pulls raw text out of a PDF, page by page
- chunk_text(): splits page text into overlapping, sentence-aware chunks
- process_pdf(): ties both together and attaches metadata (doc id, name, page number)
  so every chunk can be traced back to exactly where it came from.
"""

import re
import uuid
import logging

logger = logging.getLogger(__name__)


def extract_pages(pdf_path):
    """
    Return a list of {"page_num": int, "text": str} for every page with extractable text.

    Uses PyMuPDF (fitz) first: it's much more tolerant of the malformed cross-reference
    tables common in real-world novel/ebook PDFs (converters, scans, etc.) than pypdf,
    which silently *drops* any object it can't resolve ("Ignoring wrong pointing object ...")
    and can end up returning little or no text from an otherwise perfectly readable PDF.
    Falls back to pypdf only if PyMuPDF can't open the file at all.
    """
    pages = []
    try:
        import fitz  # PyMuPDF
        doc = fitz.open(pdf_path)
        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                pages.append({"page_num": i + 1, "text": text})
        doc.close()
        if pages:
            return pages
        logger.warning("PyMuPDF opened %s but found no extractable text; trying pypdf fallback.", pdf_path)
    except Exception as e:
        logger.warning("PyMuPDF failed to read %s (%s); falling back to pypdf.", pdf_path, e)

    from pypdf import PdfReader
    reader = PdfReader(pdf_path, strict=False)
    for i, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        text = re.sub(r"\s+", " ", text).strip()
        if text:
            pages.append({"page_num": i + 1, "text": text})
    return pages


def chunk_text(text, chunk_size=900, overlap=150):
    """
    Split text into overlapping chunks, breaking on sentence boundaries where possible
    so we don't cut sentences (and therefore meaning) in half.
    """
    if len(text) <= chunk_size:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""

    for sentence in sentences:
        # sentence itself longer than chunk_size: hard-split it
        if len(sentence) > chunk_size:
            if current:
                chunks.append(current)
                current = ""
            for start in range(0, len(sentence), chunk_size - overlap):
                chunks.append(sentence[start:start + chunk_size])
            continue

        if len(current) + len(sentence) + 1 <= chunk_size:
            current = f"{current} {sentence}".strip()
        else:
            if current:
                chunks.append(current)
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = f"{overlap_text} {sentence}".strip()

    if current:
        chunks.append(current)
    return chunks


def process_pdf(pdf_path, doc_id, doc_name, chunk_size=900, overlap=150):
    """
    Process a single PDF into a list of chunk records ready for embedding:
    {chunk_id, doc_id, doc_name, page_num, text}
    """
    pages = extract_pages(pdf_path)
    records = []
    for page in pages:
        for chunk in chunk_text(page["text"], chunk_size, overlap):
            records.append({
                "chunk_id": str(uuid.uuid4()),
                "doc_id": doc_id,
                "doc_name": doc_name,
                "page_num": page["page_num"],
                "text": chunk,
            })
    return records
