import os
import hmac
from fastapi import APIRouter, Request, Depends, Query, HTTPException
from fastapi.responses import PlainTextResponse
from starlette.concurrency import run_in_threadpool
from sqlalchemy.orm import Session
from backend.app.core.database import get_db
from backend.app.services.platform.webhooks import verify_svix, verify_meta
from backend.app.services.platform.inbound import resend, whatsapp
from backend.app.services.case_state import fail

router = APIRouter(prefix="/api/v2/connectors", tags=["Verified provider webhooks"])


async def bounded_body(request):
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > 1024 * 1024:
            fail(413, "FILE_TOO_LARGE", "Webhook exceeds 1 MiB.")
    return bytes(body)


@router.post("/inbound_email/resend/webhook")
async def received(request: Request, db: Session = Depends(get_db)):
    secret = os.getenv("RESEND_WEBHOOK_SECRET")
    if not secret:
        fail(503, "PROVIDER_NOT_CONFIGURED", "Inbound email webhook is disabled.")
    payload = verify_svix(await bounded_body(request), request.headers, secret)
    try:
        result = await run_in_threadpool(resend, db, payload)
    except HTTPException:
        raise
    except Exception:
        fail(
            502,
            "INBOUND_PROVIDER_UNAVAILABLE",
            "Inbound provider could not supply the original. Retry through the provider.",
        )
    db.commit()
    return result


@router.get("/whatsapp/webhook")
def verify(
    mode: str = Query(alias="hub.mode"),
    token: str = Query(alias="hub.verify_token"),
    challenge: str = Query(alias="hub.challenge", max_length=200),
):
    expected = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    if not expected or mode != "subscribe" or not hmac.compare_digest(expected, token):
        fail(403, "INVALID_WEBHOOK_SIGNATURE", "Webhook verification failed.")
    return PlainTextResponse(challenge)


@router.post("/whatsapp/webhook")
async def whatsapp_received(request: Request, db: Session = Depends(get_db)):
    secret = os.getenv("WHATSAPP_APP_SECRET", "")
    if not secret:
        fail(503, "PROVIDER_NOT_CONFIGURED", "WhatsApp Business webhook is disabled.")
    raw = await bounded_body(request)
    payload = verify_meta(raw, request.headers.get("X-Hub-Signature-256", ""), secret)
    result = await run_in_threadpool(whatsapp, db, payload, raw)
    db.commit()
    return result
