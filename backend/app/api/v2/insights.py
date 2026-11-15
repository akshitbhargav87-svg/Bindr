import json
from datetime import date
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import update
from pydantic import Field
from backend.app.api.v2.platform import Key
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.integrations import AggregateConsent
from backend.app.models.aggregates import Company, CompanyAssignment
from backend.app.models.case import Case
from backend.app.schemas.platform import Strict
from backend.app.services.platform.operations import execute
from backend.app.services.platform.workflow import owned_case, claim, ledger
from backend.app.services.case_state import fail

router = APIRouter(prefix="/api/v2", tags=["Private insights and official sources v2"])


class Consent(Strict):
    expected_version: int = Field(ge=0, strict=True)
    enabled: bool


@router.put("/account/aggregate-consent")
def consent(
    body: Consent,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    def save():
        row = db.get(AggregateConsent, auth.user_id)
        if row is None:
            if body.expected_version != 0:
                fail(409, "VERSION_CONFLICT", "Refresh consent settings.")
            row = AggregateConsent(
                owner_id=auth.user_id, enabled=int(body.enabled), version=1
            )
            db.add(row)
        else:
            changed = db.execute(
                update(AggregateConsent)
                .where(
                    AggregateConsent.owner_id == auth.user_id,
                    AggregateConsent.version == body.expected_version,
                )
                .values(enabled=int(body.enabled), version=body.expected_version + 1),
                execution_options={"synchronize_session": False},
            ).rowcount
            if changed != 1:
                fail(409, "VERSION_CONFLICT", "Refresh consent settings.")
            db.expire(row)
        return {
            "version": row.version,
            "enabled": bool(row.enabled),
            "public_release_enabled": False,
            "withdrawal": "Immediate exclusion from fresh aggregate computation",
        }

    return execute(db, auth.user_id, "aggregate-consent", key, body.model_dump(), save)


@router.get("/account/received-counter")
def counter(
    auth: SessionData = Depends(get_current_session), db: Session = Depends(get_db)
):
    totals = {}
    from backend.app.models.workflow import Obligation

    for case in db.query(Case).filter_by(owner_id=auth.user_id).all():
        events, _, _ = ledger(db, case.id)
        voided = {
            json.loads(e.payload)["corrects_event_id"]
            for e in events
            if e.kind == "correction"
        }
        for event in events:
            if event.kind not in ("partial", "full") or event.id in voided:
                continue
            for allocation in json.loads(event.payload)["allocations"]:
                currency = allocation.get("currency")
                if currency is None:
                    obligation = db.get(Obligation, allocation["obligation_id"])
                    currency = (
                        json.loads(obligation.terms)["currency"] if obligation else None
                    )
                if currency is not None:
                    totals[currency] = totals.get(currency, 0) + (
                        allocation["amount_minor"] or 0
                    )
    return {
        "received_minor_by_currency": totals,
        "method": "User-reported actual receipts net of void corrections; not attributable recovery caused by Bindr.",
        "legacy_v1_outcomes_included": False,
    }


@router.get("/companies/scoreboard")
def scoreboard():
    # Deliberately no env-only switch: code/privacy review must precede public release.
    fail(
        503,
        "PUBLIC_AGGREGATES_DISABLED",
        "Public aggregates require privacy and moderation approval.",
    )


@router.get("/escalation-sources")
def escalation(jurisdiction: str, auth: SessionData = Depends(get_current_session)):
    if jurisdiction != "IN":
        return {
            "sources": [],
            "reason": "No verified source registry for this jurisdiction.",
        }
    return {
        "registry_version": "2026-11-15.1",
        "sources": [
            {
                "id": "in-nch",
                "name": "National Consumer Helpline",
                "url": "https://consumerhelpline.gov.in/public/",
                "official_reference": "https://consumeraffairs.gov.in/pages/nch",
                "verified_at": "2026-11-15",
                "scope": "Indian consumer grievance information; check suitability on the official site.",
                "legal_deadline": None,
            }
        ],
        "automatic_filing": False,
        "eligibility_determined": False,
        "review_required": True,
    }


class CompanySelection(Strict):
    expected_version: int = Field(ge=1, strict=True)
    company_id: str = Field(min_length=1, max_length=80)


@router.get("/companies")
def companies(
    auth: SessionData = Depends(get_current_session), db: Session = Depends(get_db)
):
    return {
        "companies": [
            {"id": c.id, "name": c.name, "registry_version": c.registry_version}
            for c in db.query(Company).order_by(Company.name).limit(500).all()
        ],
        "registry_policy": "Curated IDs only; no automatic identity inferred from merchant wording.",
    }


@router.put("/cases/{case_id}/company")
def select_company(
    case_id: str,
    body: CompanySelection,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    case = owned_case(db, auth.user_id, case_id)
    company = db.get(Company, body.company_id)
    if company is None:
        fail(422, "UNKNOWN_COMPANY", "Select an existing reviewed company identity.")

    def save():
        claim(db, case, body.expected_version)
        assignment = db.get(CompanyAssignment, case_id)
        if assignment is None:
            assignment = CompanyAssignment(case_id=case_id, company_id=company.id)
            db.add(assignment)
        else:
            assignment.company_id = company.id
        from backend.app.services.platform.workflow import event

        event(
            db,
            case_id,
            "company_identity_selected",
            {
                "company_id": company.id,
                "registry_version": company.registry_version,
                "origin": "user_confirmed",
            },
        )
        return {
            "case_version": case.version,
            "company_id": company.id,
            "public_release_enabled": False,
        }

    return execute(
        db, auth.user_id, "case.company:" + case_id, key, body.model_dump(), save
    )


@router.get("/verification-info")
def verification_info():
    return {
        "scope": "generic_offline_instructions",
        "case_access": False,
        "uploads_required": False,
        "command": "python -m scripts.verify_evidence_bundle YOUR_DOWNLOADED_BUNDLE.zip",
        "timestamp_option": "--tsa-ca OWNER_VERIFIED_AUTHORITY_CA.pem",
        "limits": "Hashes detect altered bytes; they do not establish authorship, truth, legal certification or court acceptance. External timestamps require independent trust-anchor verification.",
    }
