"""
Automated test suite for Milestone 2: Document and Image Processing & Evidence Pipeline.
"""

import io
import sys
import unittest
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pymupdf
from PIL import Image

from backend.app.ai.schemas import (
    CommitmentExtractionResult,
    CommitmentCategory,
    CommitmentType,
    SourceMetadata,
    EvidenceMetadata,
)
from backend.app.ai.document_processor import (
    DocumentProcessor,
    ExtractedDocument,
    DocumentPage,
    DocumentProcessingError,
    UnsupportedFileTypeError,
    UnreadableDocumentError,
)
from backend.app.ai.engine import (
    PromiseExtractionEngine,
    extract_commitment_from_evidence,
)
from backend.app.ai.providers.mock import MockAIProvider


class TestDocumentProcessing(unittest.TestCase):
    """Test suite for Milestone 2 Document and Image processing."""

    def setUp(self):
        self.mock_provider = MockAIProvider()

    def _create_synthetic_pdf(self, pages_text: list[str]) -> bytes:
        """Create an in-memory text-based PDF with specified page contents."""
        doc = pymupdf.open()
        for text in pages_text:
            page = doc.new_page()
            page.insert_text((50, 72), text)
        pdf_bytes = doc.tobytes()
        doc.close()
        return pdf_bytes

    def _create_synthetic_image(self, fmt: str = "PNG") -> bytes:
        """Create a valid in-memory PNG or JPEG image."""
        img = Image.new("RGB", (200, 80), color=(255, 255, 255))
        buf = io.BytesIO()
        img.save(buf, format=fmt)
        return buf.getvalue()

    # -------------------------------------------------------------------------
    # 1. Text-based PDF extraction & page number preservation
    # -------------------------------------------------------------------------
    def test_text_based_pdf_extraction_multi_page(self):
        """Verify text extraction and page number tracking from a 2-page PDF."""
        p1 = "Dear Customer, Thank you for contacting Acme Corp."
        p2 = "We have approved your refund of $85.00 within 5-7 business days."
        pdf_bytes = self._create_synthetic_pdf([p1, p2])

        processor = DocumentProcessor()
        doc = processor.process_bytes(pdf_bytes, filename="communication.pdf")

        self.assertEqual(doc.file_type, "pdf")
        self.assertEqual(doc.filename, "communication.pdf")
        self.assertEqual(doc.total_pages, 2)
        self.assertFalse(doc.is_empty)
        self.assertEqual(len(doc.pages), 2)
        self.assertEqual(doc.pages[0].page_number, 1)
        self.assertIn("Acme Corp", doc.pages[0].text)
        self.assertEqual(doc.pages[1].page_number, 2)
        self.assertIn("refund of $85.00", doc.pages[1].text)
        self.assertIn("[Page 1]", doc.raw_text)
        self.assertIn("[Page 2]", doc.raw_text)

    # -------------------------------------------------------------------------
    # 2. PNG / JPEG image extraction
    # -------------------------------------------------------------------------
    def test_image_extraction_with_ocr_handler(self):
        """Verify screenshot processing and text extraction with OCR handler."""
        png_bytes = self._create_synthetic_image("PNG")

        def mock_ocr(img: Image.Image) -> str:
            return "Acme Corp will replace your defective blender by Monday."

        processor = DocumentProcessor(ocr_handler=mock_ocr)
        doc = processor.process_bytes(png_bytes, filename="chat_screenshot.png")

        self.assertEqual(doc.file_type, "png")
        self.assertEqual(doc.filename, "chat_screenshot.png")
        self.assertEqual(doc.total_pages, 1)
        self.assertFalse(doc.is_empty)
        self.assertIn("replace your defective blender", doc.raw_text)

    def test_jpeg_extraction_fallback_without_ocr(self):
        """Verify JPEG validation and graceful warning when no OCR handler is present."""
        jpeg_bytes = self._create_synthetic_image("JPEG")
        processor = DocumentProcessor(ocr_handler=None)

        doc = processor.process_bytes(jpeg_bytes, filename="evidence.jpg")
        self.assertEqual(doc.file_type, "jpg")
        self.assertTrue(doc.is_empty)
        self.assertTrue(len(doc.extraction_warnings) > 0)

    # -------------------------------------------------------------------------
    # 3. Unsupported file formats rejection
    # -------------------------------------------------------------------------
    def test_unsupported_file_format_rejected(self):
        """Ensure non-document/image files are rejected with UnsupportedFileTypeError."""
        processor = DocumentProcessor()
        fake_binary = b"MZ\x90\x00\x03\x00\x00\x00"

        with self.assertRaises(UnsupportedFileTypeError):
            processor.process_bytes(fake_binary, filename="malicious.exe")

        with self.assertRaises(UnsupportedFileTypeError):
            processor.process_bytes(b"some text", filename="notes.docx")

    # -------------------------------------------------------------------------
    # 4. Empty or unreadable documents
    # -------------------------------------------------------------------------
    def test_empty_file_rejected(self):
        """Ensure empty 0-byte files raise UnreadableDocumentError."""
        processor = DocumentProcessor()
        with self.assertRaises(UnreadableDocumentError):
            processor.process_bytes(b"", filename="empty.pdf")

    def test_corrupt_pdf_rejected(self):
        """Ensure corrupt PDF header raises UnreadableDocumentError."""
        processor = DocumentProcessor()
        with self.assertRaises(UnreadableDocumentError):
            processor.process_bytes(b"NOT A VALID PDF HEADER", filename="corrupt.pdf")

    def test_scanned_or_blank_pdf_flags_warning(self):
        """Ensure a PDF with no extractable text flags warnings and marks is_empty."""
        # PDF with empty blank page
        doc = pymupdf.open()
        doc.new_page()  # blank page
        pdf_bytes = doc.tobytes()
        doc.close()

        processor = DocumentProcessor()
        res = processor.process_bytes(pdf_bytes, filename="blank_scanned.pdf")
        self.assertTrue(res.is_empty)
        self.assertIn("no extractable text", res.extraction_warnings[0])

    # -------------------------------------------------------------------------
    # 5. Evidence metadata preservation & traceability
    # -------------------------------------------------------------------------
    def test_evidence_to_promise_pipeline_traceability(self):
        """Verify extract_commitment_from_evidence preserves evidence ID, filename, and page numbers."""
        pdf_text = "Acme Corp will issue your refund of $120.50 within 5-7 business days."
        pdf_bytes = self._create_synthetic_pdf([pdf_text])

        metadata = SourceMetadata(sender="Acme Corp", communication_date="2026-11-14")
        result = extract_commitment_from_evidence(
            file_source=pdf_bytes,
            filename="customer_refund.pdf",
            evidence_id="ev_abc123",
            metadata=metadata,
            provider=self.mock_provider,
        )

        # Check evidence traceability
        self.assertIsNotNone(result.evidence_metadata)
        self.assertEqual(result.evidence_metadata.evidence_id, "ev_abc123")
        self.assertEqual(result.evidence_metadata.filename, "customer_refund.pdf")
        self.assertEqual(result.evidence_metadata.file_type, "pdf")
        self.assertEqual(result.evidence_metadata.total_pages, 1)
        self.assertEqual(result.evidence_metadata.page_numbers, [1])

        # Check commitment extraction
        self.assertEqual(result.commitment_category, CommitmentCategory.REFUND)
        self.assertEqual(result.commitment_type, CommitmentType.EXPLICIT)
        self.assertEqual(result.amount, 120.50)
        self.assertEqual(result.currency, "USD")
        self.assertIsNotNone(result.supporting_quotation)
        self.assertIn("refund", result.supporting_quotation.lower())

    # -------------------------------------------------------------------------
    # 6. Unreadable document flows safely into promise result
    # -------------------------------------------------------------------------
    def test_empty_evidence_requires_user_confirmation(self):
        """Ensure an unreadable/empty document returns safe result requiring user confirmation."""
        # Blank PDF
        doc = pymupdf.open()
        doc.new_page()
        blank_pdf_bytes = doc.tobytes()
        doc.close()

        result = extract_commitment_from_evidence(
            file_source=blank_pdf_bytes,
            filename="blank.pdf",
            evidence_id="ev_empty",
            provider=self.mock_provider,
        )

        self.assertEqual(result.commitment_category, CommitmentCategory.NO_COMMITMENT)
        self.assertEqual(result.commitment_type, CommitmentType.NONE)
        self.assertTrue(result.user_confirmation_required)
        self.assertIn("unreadable_evidence", result.missing_or_ambiguous_fields)
        self.assertEqual(result.evidence_metadata.evidence_id, "ev_empty")


if __name__ == "__main__":
    unittest.main()
