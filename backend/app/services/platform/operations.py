"""Replay-safe transactions. Unique reservation serializes matching operations in PostgreSQL."""

import hashlib
import json
from sqlalchemy.exc import IntegrityError
from backend.app.models.platform import Operation
from backend.app.services.case_state import fail


def canonical(value):
    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def execute(db, owner, scope, key, payload, mutation):
    digest = hashlib.sha256(canonical(payload).encode()).hexdigest()
    identity = (owner, scope, key)

    def replay(row):
        if row.payload_hash != digest:
            fail(
                409,
                "IDEMPOTENCY_CONFLICT",
                "Operation key was already used with different data.",
            )
        if row.result is None:
            fail(
                409,
                "OPERATION_IN_PROGRESS",
                "Reconcile this operation before retrying.",
            )
        return json.loads(row.result)

    previous = db.get(Operation, identity)
    if previous:
        return replay(previous)
    operation = Operation(owner_id=owner, scope=scope, key=key, payload_hash=digest)
    db.add(operation)
    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        previous = db.get(Operation, identity)
        if previous is None:
            raise
        return replay(previous)
    try:
        result = mutation()
        operation.result = canonical(result)
        db.commit()
        return result
    except BaseException:
        db.rollback()
        raise
