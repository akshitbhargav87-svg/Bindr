"""Private static calendar export. It does not subscribe, push, or update a user's calendar."""

import json
from datetime import datetime, timezone
from backend.app.models.workflow import Obligation
from backend.app.services.platform.workflow import owned_case


def escape(value):
    return (
        value.replace("\\", "\\\\")
        .replace("\r", "")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def fold(value):
    output = []
    line = ""
    size = 0
    for char in value:
        encoded = len(char.encode("utf-8"))
        if size + encoded > 73:
            output.append(line)
            line = " "
            size = 1
        line += char
        size += encoded
    return "\r\n".join(output + [line])


def calendar(db, owner, case_id):
    case = owned_case(db, owner, case_id)
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Bindr//Private snapshot v2//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    for row in db.query(Obligation).filter_by(case_id=case_id, state="active").all():
        terms = json.loads(row.terms)
        if not terms["due_at"]:
            continue
        due = (
            datetime.fromisoformat(terms["due_at"].replace("Z", "+00:00"))
            .astimezone(timezone.utc)
            .strftime("%Y%m%dT%H%M%SZ")
        )
        lines += [
            "BEGIN:VEVENT",
            "UID:" + row.id + "@bindr.invalid",
            "SEQUENCE:" + str(case.version),
            "DTSTAMP:" + stamp,
            "DTSTART:" + due,
            "SUMMARY:" + escape(case.merchant_name + ": " + terms["description"]),
            "DESCRIPTION:"
            + escape(
                "Static private export; refresh from Bindr after edits. Case version "
                + str(case.version)
            ),
            "END:VEVENT",
        ]
    lines += ["END:VCALENDAR"]
    return ("\r\n".join(fold(line) for line in lines) + "\r\n").encode("utf-8")
