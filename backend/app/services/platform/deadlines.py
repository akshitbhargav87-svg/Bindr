"""Reproducible date arithmetic; never interprets source language or legal deadlines."""

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def preview(body, now=None):
    now = now or datetime.now(ZoneInfo(body.anchor.timezone))
    policy = {
        "id": body.calendar_id,
        "version": body.calendar_version,
        "weekends": body.weekends,
        "holidays": sorted(d.isoformat() for d in body.holidays),
        "coverage": (
            "user_supplied"
            if body.calendar_id == "custom"
            else "weekends_only_no_holiday_coverage"
        ),
    }
    result = {
        "earliest": None,
        "latest": None,
        "status": "anchor_missing",
        "timezone": body.anchor.timezone,
        "anchor": body.anchor.model_dump(mode="json"),
        "expression": body.expression,
        "calendar": policy,
        "counting_rule": "exclude_anchor_include_final_date",
        "warnings": [],
        "explanation": "",
    }
    if body.conditional and body.condition_fulfilled is not True:
        result.update(
            status="condition_unconfirmed",
            explanation="The trigger is not confirmed. No deadline calculated.",
        )
        return result
    if (
        body.anchor.date
        and body.anchor.date > now.astimezone(ZoneInfo(body.anchor.timezone)).date()
    ):
        result["warnings"].append("future_communication_date_requires_confirmation")
    if body.unit == "explicit_date":
        dates = [body.explicit_date, body.explicit_date]
    elif not body.anchor_confirmed or body.anchor.date is None:
        result["explanation"] = (
            "A confirmed communication or event anchor is required; upload time is never substituted."
        )
        return result
    else:

        def add(count):
            day = body.anchor.date
            while count:
                day += timedelta(days=1)
                if body.unit == "calendar_days" or (
                    day.weekday() not in body.weekends and day not in body.holidays
                ):
                    count -= 1
            return day

        dates = [add(body.minimum), add(body.maximum)]
    result.update(
        status="proposal",
        earliest=dates[0].isoformat(),
        latest=dates[1].isoformat(),
        explanation=f"{body.minimum}–{body.maximum} {body.unit}; anchor excluded. Confirm the final date and timezone before saving.",
    )
    # Only an explicit source/anchor clock can produce an instant.
    clock = body.explicit_time or body.anchor.time
    result["earliest_at"] = None
    result["latest_at"] = None
    if clock is not None:
        zone = ZoneInfo(body.anchor.timezone)
        instants = []
        for day in dates:
            candidate = datetime.combine(day, clock, zone)
            roundtrip = candidate.astimezone(timezone.utc).astimezone(zone)
            alternate = candidate.replace(fold=1)
            if (
                roundtrip.replace(tzinfo=None) != candidate.replace(tzinfo=None)
                or candidate.utcoffset() != alternate.utcoffset()
            ):
                result["warnings"].append(
                    "ambiguous_or_nonexistent_local_time_requires_explicit_offset"
                )
                instants.append(None)
            else:
                instants.append(candidate.isoformat())
        result["earliest_at"], result["latest_at"] = instants
    return result


def attach(row, selection, terms, override_reason):
    if selection is None:
        return
    from backend.app.services.platform.operations import canonical
    from backend.app.services.case_state import fail

    proposal = preview(selection)
    final = (
        terms.due_at.astimezone(ZoneInfo(selection.anchor.timezone)).date().isoformat()
        if terms.due_at
        else None
    )
    if (
        final
        and (proposal["status"] != "proposal" or final != proposal["latest"])
        and not override_reason
    ):
        fail(
            422,
            "OVERRIDE_REASON_REQUIRED",
            "Explain why the confirmed date differs from the deterministic proposal.",
        )
    row.deadline = canonical(
        {
            "input": selection.model_dump(mode="json"),
            "proposal": proposal,
            "confirmed_due_at": terms.model_dump(mode="json")["due_at"],
            "override_reason": override_reason,
        }
    )
