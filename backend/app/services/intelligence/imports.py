"""Bounded, data-only import adapters. Original bytes remain A's immutable evidence."""
from __future__ import annotations
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from time import monotonic
import pymupdf
from PIL import Image
from backend.app.ai.document_processor import DocumentProcessor, UnreadableDocumentError
from .contracts import Segment


class TextHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.hidden = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "iframe", "object"}:
            self.hidden += 1
        if tag in {"p", "br", "div", "li"}:
            self.parts.append("\n")

    def handle_endtag(self, tag):
        if tag in {"script", "style", "iframe", "object"} and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def html_text(html):
    parser = TextHTML()
    parser.feed(html)
    return "".join(parser.parts).strip()


class ImportProcessor:
    MAX_BYTES = 10 * 1024 * 1024

    def __init__(self, documents=None, msg_parser=None, transcription=None, seconds=20):
        self.documents = documents or DocumentProcessor()
        self.msg_parser, self.transcription, self.seconds = msg_parser, transcription, seconds

    def process(self, content, filename):
        if not isinstance(content, bytes) or not 0 < len(content) <= self.MAX_BYTES:
            raise UnreadableDocumentError("Use a nonempty original up to 10 MiB.")
        started = monotonic()
        ext = Path(filename).suffix.lower()
        if ext == ".pdf":
            result = self._pdf(content, started)
        elif ext == ".eml":
            result = self._email(content)
        elif ext == ".msg":
            if not self.msg_parser:
                raise UnreadableDocumentError("MSG decoder is not configured. Export as EML or paste the message.")
            # Decoder injection stays optional until A approves/pins its runtime dependency.
            decoded = self.msg_parser(content)
            result = {"segments": [Segment(text=decoded["text"], message_id="msg-1").model_dump()],
                      "headers": decoded.get("headers", {}), "attachments": decoded.get("attachments", []),
                      "warnings": ["Imported message headers are claims, not authenticated provenance."] + decoded.get("warnings", [])}
        elif ext in {".wav", ".mp3", ".m4a", ".ogg"}:
            if not self.transcription:
                raise UnreadableDocumentError("Transcription is not configured. Attach a transcript or enter the promise manually.")
            transcript = self.transcription(content, filename=filename, timeout=self.seconds)
            if not isinstance(transcript, list) or len(transcript) > 100:
                raise UnreadableDocumentError("Transcript exceeds the segment limit.")
            segments = [Segment.model_validate(s).model_dump() for s in transcript]
            if any(s["start_ms"] is None for s in segments):
                raise UnreadableDocumentError("Transcription must preserve audio offsets.")
            result = {"segments": segments, "attachments": [], "warnings": ["Transcript and speaker attribution require review against the original audio."]}
        else:
            doc = self.documents.process_bytes(content, filename)
            result = {"segments": [Segment(text=p.text, page=p.page_number).model_dump() for p in doc.pages if p.text],
                      "attachments": [], "warnings": doc.extraction_warnings}
        if monotonic()-started > self.seconds:
            raise UnreadableDocumentError("Import exceeded its processing budget. Use a smaller source or a background job.")
        if sum(len(s["text"]) for s in result["segments"]) > 50000:
            raise UnreadableDocumentError("Import exceeds 50,000 characters. Split the source explicitly.")
        if not result["segments"]:
            raise UnreadableDocumentError("No readable source text. Review manually or attach a clearer original.")
        return result

    def _pdf(self, content, started):
        segments, warnings = [], []
        try:
            with pymupdf.open(stream=content, filetype="pdf") as doc:
                if doc.needs_pass or not 0 < len(doc) <= 50:
                    raise UnreadableDocumentError("PDF is encrypted, empty or exceeds 50 pages.")
                chars = 0
                for index, page in enumerate(doc):
                    if monotonic()-started > self.seconds:
                        raise UnreadableDocumentError("PDF processing budget exhausted.")
                    text = (page.get_text() or "").strip()
                    if len(text) >= 20 and page.get_images():
                        warnings.append(f"Page {index+1}: text layer reused; image-only details on this page require visual review.")
                    # Reuse good text. OCR only pages lacking meaningful text, preserving page identity.
                    if len(text) < 20 and page.get_images():
                        width, height = page.rect.width, page.rect.height
                        scale = min(2, (12_000_000 / max(1, width*height)) ** 0.5)
                        pix = page.get_pixmap(matrix=pymupdf.Matrix(scale, scale), alpha=False)
                        scanned = self.documents.process_bytes(pix.tobytes("png"), "page.png")
                        if scanned.raw_text.strip():
                            text = scanned.raw_text
                        warnings.append(f"Page {index+1}: OCR used; verify wording against the original.")
                        warnings.extend(scanned.extraction_warnings)
                    chars += len(text)
                    if chars > 50000:
                        raise UnreadableDocumentError("PDF exceeds 50,000 characters.")
                    if text:
                        segments.append(Segment(text=text, page=index+1).model_dump())
                    else:
                        warnings.append(f"Page {index+1}: no readable text; extraction is incomplete.")
        except UnreadableDocumentError:
            raise
        except Exception:
            raise UnreadableDocumentError("PDF could not be parsed. Preserve the original and review manually.") from None
        return {"segments": segments, "attachments": [], "warnings": warnings}

    def _email(self, content):
        try:
            message = BytesParser(policy=policy.default).parsebytes(content)
        except (ValueError, RecursionError):
            raise UnreadableDocumentError("Email MIME structure could not be parsed safely.") from None
        headers = {k: str(message.get(k, ""))[:2000] for k in ("From", "To", "Date", "Subject", "Message-ID")}
        parts, stack = [], [(message, 0)]
        while stack:
            part, depth = stack.pop()
            parts.append(part)
            if depth > 5 or len(parts) > 40:
                raise UnreadableDocumentError("Email exceeds five nesting levels or 40 MIME parts.")
            if part.is_multipart():
                stack.extend((child, depth+1) for child in reversed(list(part.iter_parts())))
        plain, html, attachments = [], [], []
        for part in parts:
            if part.is_multipart():
                continue
            data = part.get_payload(decode=True) or b""
            if len(data) > self.MAX_BYTES:
                raise UnreadableDocumentError("Email attachment exceeds size limit.")
            if part.get_filename() or part.get_content_disposition() == "attachment":
                if len(attachments) >= 10:
                    raise UnreadableDocumentError("Email exceeds 10 attachments.")
                name = (part.get_filename() or "attachment").replace("\\", "/").split("/")[-1]
                attachments.append({"filename": name[:200], "bytes": data, "claimed_type": part.get_content_type()})
                continue
            mime = part.get_content_type()
            if mime in {"text/plain", "text/html"}:
                try:
                    text = data.decode(part.get_content_charset() or "utf-8", errors="replace")
                except LookupError:
                    raise UnreadableDocumentError("Email body declares an unsupported character encoding.") from None
                (plain if mime == "text/plain" else html).append(text)
        body = "\n".join(plain) if plain else html_text("\n".join(html))
        return {"headers": headers,
                "segments": [Segment(text=body, message_id=headers["Message-ID"] or "message-1").model_dump()] if body.strip() else [],
                "attachments": attachments,
                "warnings": ["Message headers/quoted threads are claims, not authenticated sender provenance.",
                             "Attachments require separate authorized ingest; no remote images or resources were loaded."]}
