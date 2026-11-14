"""
Document and image processing service for Milestone 2 evidence extraction.

Supports text extraction from:
- PNG images
- JPG/JPEG images
- Text-based PDF documents (via PyMuPDF)
- Plain text files (.txt)
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import List, Optional, Union, Callable
from pydantic import BaseModel, Field

import pymupdf
from PIL import Image


class DocumentProcessingError(Exception):
    """Base exception for document and evidence processing errors."""
    pass


class UnsupportedFileTypeError(DocumentProcessingError):
    """Raised when an unsupported file extension or MIME type is uploaded."""
    pass


class UnreadableDocumentError(DocumentProcessingError):
    """Raised when a file is corrupted, empty, or unparseable."""
    pass


class DocumentPage(BaseModel):
    """Page-level extracted text and metadata."""
    page_number: int = Field(description="1-indexed page number.")
    text: str = Field(description="Extracted text content of this page.")


class ExtractedDocument(BaseModel):
    """Structured representation of extracted document evidence."""
    raw_text: str = Field(description="Combined text from all pages/sections.")
    pages: List[DocumentPage] = Field(default_factory=list, description="Per-page text extractions.")
    file_type: str = Field(description="Normalized file format: 'pdf', 'png', 'jpg', 'jpeg'.")
    filename: Optional[str] = Field(default=None, description="Original filename if known.")
    total_pages: int = Field(default=1, description="Total number of pages processed.")
    is_empty: bool = Field(default=False, description="True if no readable text could be found.")
    extraction_warnings: List[str] = Field(default_factory=list, description="Any warnings logged during extraction.")


class DocumentProcessor:
    """
    Validates, parses, and extracts text from screenshot images and PDF documents.
    Does not persist files permanently to disk.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".txt"}

    # Magic byte signatures for content validation
    MAGIC_BYTES = {
        "pdf": b"%PDF",
        "png": b"\x89PNG\r\n\x1a\n",
        "jpeg": b"\xff\xd8\xff",
    }

    def __init__(self, ocr_handler: Optional[Callable[[Image.Image], str]] = None):
        """
        Args:
            ocr_handler: Optional custom OCR function accepting a PIL Image and returning text.
                         If None, checks for pytesseract or returns an informative warning.
        """
        self.ocr_handler = ocr_handler

    def process_file(self, file_path: Union[str, Path]) -> ExtractedDocument:
        """
        Extract readable text from a file on disk.

        Args:
            file_path: Absolute or relative path to evidence file.

        Returns:
            ExtractedDocument containing text and metadata.
        """
        path = Path(file_path)
        if not path.is_file():
            raise UnreadableDocumentError(f"Evidence file not found: {file_path}")

        try:
            with open(path, "rb") as f:
                content = f.read()
        except Exception as e:
            raise UnreadableDocumentError(f"Failed to read file '{path.name}': {e}") from e

        return self.process_bytes(content, filename=path.name)

    def process_bytes(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """
        Extract readable text from in-memory byte buffer.

        Args:
            file_bytes: Raw bytes of the document/image.
            filename: Original filename (used for extension detection).

        Returns:
            ExtractedDocument containing text and metadata.
        """
        if not file_bytes:
            raise UnreadableDocumentError(f"Evidence file '{filename}' is empty (0 bytes).")

        ext = Path(filename).suffix.lower()
        if ext not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedFileTypeError(
                f"Unsupported file format '{ext}' for file '{filename}'. "
                f"Supported formats: {', '.join(sorted(self.SUPPORTED_EXTENSIONS))}"
            )

        if ext == ".pdf":
            return self._extract_pdf(file_bytes, filename=filename)
        elif ext in {".png", ".jpg", ".jpeg"}:
            return self._extract_image(file_bytes, filename=filename, ext=ext.lstrip("."))
        elif ext == ".txt":
            return self._extract_text(file_bytes, filename=filename)

        raise UnsupportedFileTypeError(f"Unsupported file format '{ext}'")

    def _extract_pdf(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """Extract text from text-based PDF using PyMuPDF."""
        if not file_bytes.startswith(b"%PDF"):
            raise UnreadableDocumentError(f"File '{filename}' does not appear to be a valid PDF (invalid magic header).")

        try:
            pdf_doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            raise UnreadableDocumentError(f"PyMuPDF failed to parse PDF '{filename}': {e}") from e

        pages: List[DocumentPage] = []
        combined_text_parts: List[str] = []
        warnings: List[str] = []

        total_pages = len(pdf_doc)
        if total_pages == 0:
            pdf_doc.close()
            return ExtractedDocument(
                raw_text="",
                pages=[],
                file_type="pdf",
                filename=filename,
                total_pages=0,
                is_empty=True,
                extraction_warnings=["PDF contains 0 pages."],
            )

        for page_idx in range(total_pages):
            page = pdf_doc[page_idx]
            page_text = (page.get_text() or "").strip()
            pages.append(DocumentPage(page_number=page_idx + 1, text=page_text))
            if page_text:
                combined_text_parts.append(f"[Page {page_idx + 1}]\n{page_text}")

        pdf_doc.close()

        combined_text = "\n\n".join(combined_text_parts).strip()
        is_empty = len(combined_text) == 0

        if is_empty:
            warnings.append(
                "PDF contains no extractable text layer. "
                "The file may be a scanned image-only PDF without embedded OCR text."
            )

        return ExtractedDocument(
            raw_text=combined_text,
            pages=pages,
            file_type="pdf",
            filename=filename,
            total_pages=total_pages,
            is_empty=is_empty,
            extraction_warnings=warnings,
        )

    def _extract_image(self, file_bytes: bytes, filename: str, ext: str) -> ExtractedDocument:
        """Validate and extract text from PNG/JPG/JPEG screenshots."""
        try:
            image = Image.open(io.BytesIO(file_bytes))
            image.verify()  # Verify image integrity
            # Reopen because verify() consumes image stream
            image = Image.open(io.BytesIO(file_bytes))
        except Exception as e:
            raise UnreadableDocumentError(f"Failed to parse image '{filename}': {e}") from e

        warnings: List[str] = []
        extracted_text = ""

        # Use injected OCR handler if provided (for testing/custom engines)
        if self.ocr_handler:
            try:
                extracted_text = (self.ocr_handler(image) or "").strip()
            except Exception as e:
                warnings.append(f"OCR handler failure: {e}")
        else:
            # Default to RapidOCR with onnxruntime
            try:
                import numpy as np
                from rapidocr import RapidOCR
                engine = RapidOCR()
                output = engine(np.array(image.convert("RGB")))
                if output and output.txts:
                    extracted_text = "\n".join(output.txts).strip()
            except ImportError:
                # Optional fallback check for pytesseract
                try:
                    import pytesseract
                    extracted_text = pytesseract.image_to_string(image).strip()
                except (ImportError, Exception):
                    warnings.append(
                        f"No active OCR engine installed on host for image '{filename}'. "
                        f"Image metadata preserved ({image.width}x{image.height} {image.format})."
                    )
            except Exception as e:
                warnings.append(f"RapidOCR extraction failure for image '{filename}': {e}")

        is_empty = len(extracted_text) == 0
        if is_empty and not warnings:
            warnings.append(f"Image '{filename}' contains no readable text.")

        page = DocumentPage(page_number=1, text=extracted_text)

        return ExtractedDocument(
            raw_text=extracted_text,
            pages=[page],
            file_type=ext,
            filename=filename,
            total_pages=1,
            is_empty=is_empty,
            extraction_warnings=warnings,
        )

    def _extract_text(self, file_bytes: bytes, filename: str) -> ExtractedDocument:
        """Extract content from a plain-text (.txt) file.

        Attempts UTF-8 decoding first; falls back to latin-1 to handle
        common single-byte encoded files without raising an error.
        """
        warnings: List[str] = []
        try:
            text = file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = file_bytes.decode("latin-1")
                warnings.append(f"Text file '{filename}' decoded using latin-1 fallback (not valid UTF-8).")
            except Exception as e:
                raise UnreadableDocumentError(f"Cannot decode text file '{filename}': {e}") from e

        text = text.strip()
        is_empty = len(text) == 0
        if is_empty:
            warnings.append(f"Text file '{filename}' contains no readable content.")

        page = DocumentPage(page_number=1, text=text)

        return ExtractedDocument(
            raw_text=text,
            pages=[page],
            file_type="txt",
            filename=filename,
            total_pages=1,
            is_empty=is_empty,
            extraction_warnings=warnings,
        )
