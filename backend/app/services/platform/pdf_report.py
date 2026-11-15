"""Paginated factual report with local previews and a generic, non-case verifier QR."""

import html
import io
import os
from urllib.parse import urlparse
import pymupdf


def qr_url():
    value = os.getenv("BINDR_VERIFIER_URL", "")
    if not value:
        return None
    parsed = urlparse(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path != "/api/v2/verification-info"
    ):
        raise ValueError(
            "Verifier URL must be a generic HTTPS /api/v2/verification-info URL without case IDs or query parameters"
        )
    return value


def render(record, wording, previews=None):
    escape = lambda value: html.escape(str(value))
    case = record["case"]
    projection = record["projection"]
    archive = pymupdf.Archive()

    def money(value, currency):
        if value is None:
            return "Not financial"
        scale = 1 if currency == "JPY" else 100
        whole, fraction = divmod(value, scale)
        return (
            escape(currency)
            + " "
            + (str(whole) if scale == 1 else f"{whole}.{fraction:02d}")
        )

    parts = [
        "<h1>Bindr case snapshot</h1>",
        f'<h2>{escape(case["title"])}</h2>',
        f'<p>{escape(case["merchant_name"])} · Case {escape(case["id"])}</p>',
        f'<p>Version {case["version"]} · Exported {escape(projection["as_of"])} · Timezone {escape(projection["timezone"])}</p>',
        "<p>Original bytes remain in the bundle. This report does not certify authorship, truth or legal admissibility.</p>",
        "<h2>Reviewed wording</h2><p>" + escape(wording).replace("\n", "<br>") + "</p>",
        "<h2>Confirmed promises and history</h2>",
    ]
    for obligation in record["obligations"]:
        terms = obligation["terms"]
        parts += [
            f'<h3>{escape(terms["description"])}</h3>',
            f'<p>ID {escape(obligation["id"])} · {escape(obligation["semantic_status"])} · Origin: {escape(obligation["origin"])}</p>',
        ]
        if terms["amount_minor"] is not None:
            parts.append(
                "<p>Promised "
                + money(terms["amount_minor"], terms["currency"])
                + " · Received "
                + money(obligation["received_minor"], terms["currency"])
                + " · Outstanding "
                + money(obligation["outstanding_minor"], terms["currency"])
                + "</p>"
            )
        parts.append(
            "<p>Confirmed deadline: " + escape(terms["due_at"] or "Undated") + "</p>"
        )
        if obligation["predecessor_id"]:
            parts.append(
                "<p>Revises "
                + escape(obligation["predecessor_id"])
                + ". The predecessor remains above/below in this history.</p>"
            )
        if obligation["deadline"]:
            calculation = obligation["deadline"].get("proposal", {})
            parts.append(
                "<p>Calculated window: "
                + escape(calculation.get("earliest"))
                + " to "
                + escape(calculation.get("latest"))
                + " · "
                + escape(calculation.get("timezone"))
                + "<br>"
                + escape(calculation.get("explanation"))
                + "<br>Override reason: "
                + escape(obligation["deadline"].get("override_reason") or "None")
                + "</p>"
            )
        for source in obligation["sources"]:
            parts.append(
                "<p>Source "
                + escape(source["evidence_id"])
                + (" · page " + escape(source["page"]) if source.get("page") else "")
                + "</p><blockquote>"
                + escape(source["quote"]).replace("\n", "<br>")
                + "</blockquote>"
            )
    if record.get("legacy_commitments"):
        parts.append("<h2>Legacy v1 confirmed records</h2>")
        for legacy in record["legacy_commitments"]:
            parts.append(
                "<p><b>"
                + escape(legacy["description"])
                + "</b><br>"
                + escape(legacy["status"])
                + " · "
                + money(legacy.get("amount_minor"), legacy.get("currency"))
                + " · Deadline: "
                + escape(legacy.get("due_at") or "Undated")
                + "</p>"
            )
    parts.append("<h2>Outcome and activity ledger</h2>")
    for event in record["events"][:200]:
        payload = event["payload"]
        details = []
        if payload.get("note"):
            details.append(escape(payload["note"]))
        if payload.get("text"):
            details.append(escape(payload["text"]))
        if payload.get("reason"):
            details.append("Reason: " + escape(payload["reason"]))
        if payload.get("corrects_event_id"):
            details.append("Corrects event " + escape(payload["corrects_event_id"]))
        if payload.get("allocations"):
            for allocation in payload["allocations"]:
                obligation = next(
                    (
                        o
                        for o in record["obligations"]
                        if o["id"] == allocation["obligation_id"]
                    ),
                    None,
                )
                currency = obligation["terms"]["currency"] if obligation else None
                details.append(
                    "Promise "
                    + escape(allocation["obligation_id"])
                    + " · "
                    + money(allocation.get("amount_minor"), currency)
                )
        parts.append(
            "<p><b>"
            + escape(event["kind"].replace("_", " ").capitalize())
            + "</b> · "
            + escape(event["created_at"])
            + "<br>"
            + "<br>".join(details)
            + "</p>"
        )
    if len(record["events"]) > 200:
        parts.append(
            "<p>The report shows the first 200 events. The complete ledger is in record.json.</p>"
        )
    parts.append("<h2>Selected original references</h2>")
    if not record.get("evidence"):
        parts.append("<p>No original files selected for this snapshot.</p>")
    for evidence in record.get("evidence", []):
        parts.append(
            "<p>"
            + escape(evidence["filename"])
            + " · "
            + escape(evidence["id"])
            + "<br>SHA-256 "
            + escape(evidence["sha256"])
            + "<br>Imported: "
            + escape(evidence.get("created_at"))
            + "; communication: "
            + escape(evidence.get("communication") or "Unknown")
            + "</p>"
        )
    for index, (name, data) in enumerate(previews or []):
        path = "preview-" + str(index) + ".png"
        archive.add((data, path))
        parts.append(
            "<h3>Preview: "
            + escape(name)
            + '</h3><p>Preview only. Use the original file and digest for byte verification.</p><img src="'
            + path
            + '" width="480">'
        )
    url = qr_url()
    if url:
        import qrcode

        buffer = io.BytesIO()
        qrcode.make(url).save(buffer, format="PNG")
        archive.add((buffer.getvalue(), "verifier.png"))
        parts.append(
            '<h2>Verify the downloaded bundle</h2><p>This QR opens generic offline verification instructions. It grants no access to this case.</p><img src="verifier.png" width="128"><p>'
            + escape(url)
            + "</p>"
        )
    parts.append(
        "<p>Private downloaded copies can be read by anyone you share them with. Bindr receipt time differs from an externally verified timestamp; inspect record.tsr only when present.</p>"
    )
    output = io.BytesIO()
    writer = pymupdf.DocumentWriter(output)
    story = pymupdf.Story(
        html="".join(parts),
        archive=archive,
        user_css="body {font-family:sans-serif;font-size:10pt;line-height:1.4} h1 {font-size:24pt} h2 {font-size:15pt;margin-top:18pt} h3 {font-size:12pt} p,blockquote {overflow-wrap:anywhere} blockquote {margin-left:12pt;color:#333}",
    )
    more = True
    pages = 0
    while more:
        pages += 1
        if pages > 200:
            raise ValueError("PDF exceeds report page limit; use data export")
        device = writer.begin_page(pymupdf.Rect(0, 0, 595, 842))
        more, _ = story.place(pymupdf.Rect(40, 40, 555, 802))
        story.draw(device)
        writer.end_page()
    writer.close()
    with pymupdf.open(stream=output.getvalue(), filetype="pdf") as document:
        for index, page in enumerate(document):
            page.insert_text(
                (40, 825),
                f"Bindr snapshot | Page {index+1} of {len(document)}",
                fontsize=8,
            )
        return document.tobytes()
