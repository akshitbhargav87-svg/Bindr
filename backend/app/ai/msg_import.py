"""Optional extract-msg adapter. Runtime pin/activation belongs to A."""
from backend.app.ai.document_processor import UnreadableDocumentError


def parse_msg(content):
    if not content.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"):
        raise UnreadableDocumentError("MSG original does not have a valid compound-file header.")
    try:
        import extract_msg
    except ImportError:
        raise UnreadableDocumentError("MSG decoder is not installed. Export as EML or paste the source.") from None
    from backend.app.services.intelligence.imports import html_text
    try:
        with extract_msg.Message(content) as message:
            body = message.body
            if not body and message.htmlBody:
                html = message.htmlBody
                body = html_text(html.decode("utf-8", errors="replace") if isinstance(html, bytes) else html)
            if not body or len(body) > 50000:
                raise UnreadableDocumentError("MSG body is empty or exceeds 50,000 characters.")
            if len(message.attachments) > 10:
                raise UnreadableDocumentError("MSG exceeds ten attachments.")
            attachments, warnings, total = [], [], 0
            for attachment in message.attachments:
                data = attachment.data
                if not isinstance(data, bytes):
                    warnings.append("Embedded message attachment retained in the original; recursive parsing disabled.")
                    continue
                total += len(data)
                if total > 10*1024*1024:
                    raise UnreadableDocumentError("MSG decoded attachments exceed ten MiB.")
                filename = (attachment.longFilename or attachment.shortFilename or "attachment").replace("\\", "/").split("/")[-1][:200]
                attachments.append({"filename": filename, "bytes": data, "claimed_type": "application/octet-stream"})
            return {"text": body, "headers": {"From": str(message.sender or "")[:2000],
                                              "To": str(message.to or "")[:2000], "Date": str(message.date or "")[:2000],
                                              "Subject": str(message.subject or "")[:2000]},
                    "attachments": attachments, "warnings": warnings}
    except UnreadableDocumentError:
        raise
    except Exception:
        raise UnreadableDocumentError("MSG could not be decoded. Preserve the original and review manually.") from None
