"""Private computation until privacy/moderation approval. Fresh queries honor withdrawal immediately."""

import json
from datetime import datetime, timezone
from backend.app.models.case import Case
from backend.app.models.workflow import Obligation
from backend.app.models.integrations import AggregateConsent
from backend.app.models.aggregates import CompanyAssignment
from backend.app.services.platform.workflow import ledger

MIN_ACCOUNTS = 20


def company_summary(db, company_id, start, end):
    participating = (
        db.query(Case)
        .join(CompanyAssignment, CompanyAssignment.case_id == Case.id)
        .join(AggregateConsent, AggregateConsent.owner_id == Case.owner_id)
        .filter(
            CompanyAssignment.company_id == company_id, AggregateConsent.enabled == 1
        )
        .all()
    )
    accounts = set()
    received_by_currency = {}
    obligations = 0
    fulfilled = 0
    for case in participating:
        events, receipts, full = ledger(db, case.id)
        eligible = [
            o
            for o in db.query(Obligation)
            .filter_by(case_id=case.id, state="active")
            .all()
            if start <= o.created_at[:10] <= end
        ]
        if not eligible:
            continue
        accounts.add(case.owner_id)
        for row in eligible:
            terms = json.loads(row.terms)
            amount = terms["amount_minor"]
            got = receipts.get(row.root_id, 0)
            obligations += 1
            if row.root_id in full or amount is not None and got >= amount:
                fulfilled += 1
            if amount is not None:
                received_by_currency[terms["currency"]] = (
                    received_by_currency.get(terms["currency"], 0) + got
                )
    if len(accounts) < MIN_ACCOUNTS:
        return {
            "suppressed": True,
            "reason": "insufficient_distinct_participants",
            "minimum_participants": MIN_ACCOUNTS,
        }
    return {
        "suppressed": False,
        "company_id": company_id,
        "distinct_participants": len(accounts),
        "denominator_obligations": obligations,
        "fulfilled_obligations": fulfilled,
        "received_minor_by_currency": received_by_currency,
        "period": {"cohort_confirmed_from": start, "cohort_confirmed_to": end},
        "method": "Self-reported opted-in active obligation cohorts; receipt totals include subsequent receipts and void corrections. Revisions count once by active root. Participation is self-selected; this does not represent all customers.",
        "as_of": datetime.now(timezone.utc).isoformat(),
    }
