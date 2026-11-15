import hashlib
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import Field
from backend.app.api.v2.platform import Key
from backend.app.core.auth import get_current_session, SessionData
from backend.app.core.database import get_db
from backend.app.models.devices import PushDevice
from backend.app.schemas.platform import Strict
from backend.app.services.platform.credentials import seal
from backend.app.services.platform.operations import execute
from backend.app.services.case_state import fail

router = APIRouter(
    prefix="/api/v2/notification-devices",
    tags=["Private push registration proposal v1"],
)


class Register(Strict):
    token: str = Field(min_length=20, max_length=4096)


@router.post("", status_code=201)
def register(
    body: Register,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    def save():
        digest = hashlib.sha256(body.token.encode()).hexdigest()
        existing = db.query(PushDevice).filter_by(token_digest=digest).first()
        if existing and existing.owner_id != auth.user_id:
            fail(
                409,
                "DEVICE_BOUND",
                "Disconnect this device from the prior account first.",
            )
        if (
            db.query(PushDevice).filter_by(owner_id=auth.user_id, active=1).count()
            >= 10
            and existing is None
        ):
            fail(429, "DEVICE_LIMIT", "Device limit reached.")
        row = existing or PushDevice(owner_id=auth.user_id, token_digest=digest)
        row.credential = seal(auth.user_id, "fcm", {"token": body.token})
        row.active = 1
        db.add(row)
        db.flush()
        return {"device_id": row.id, "state": "registered", "delivery_verified": False}

    # Store a hash as the operation fingerprint input, not the raw device token.
    return execute(
        db,
        auth.user_id,
        "push.register",
        key,
        {"token_digest": hashlib.sha256(body.token.encode()).hexdigest()},
        save,
    )


@router.delete("/{device_id}")
def unregister(
    device_id: str,
    key: Key,
    auth: SessionData = Depends(get_current_session),
    db: Session = Depends(get_db),
):
    row = db.query(PushDevice).filter_by(id=device_id, owner_id=auth.user_id).first()
    if row is None:
        fail(404, "NOT_FOUND", "Device not found.")

    def save():
        row.active = 0
        row.credential = ""
        return {"state": "disconnected"}

    return execute(db, auth.user_id, "push.remove:" + device_id, key, {}, save)
