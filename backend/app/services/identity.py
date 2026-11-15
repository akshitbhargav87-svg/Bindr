"""Google Identity Platform boundary; no local password or TOTP implementation."""
from functools import lru_cache
import hashlib
import json
from backend.app.core.config import settings


class IdentityUnavailable(Exception):
    pass


class InvalidIdentity(Exception):
    pass


def factor_version(user):
    factors = user.get("mfaInfo", [])
    return hashlib.sha256(json.dumps(factors, sort_keys=True).encode()).hexdigest()


class GoogleIdentity:
    def __init__(self):
        import firebase_admin
        from google.auth.transport.requests import AuthorizedSession
        import google.auth
        try:
            self.app = firebase_admin.get_app("bindr")
        except ValueError:
            self.app = firebase_admin.initialize_app(options={"projectId": settings.FIREBASE_PROJECT_ID}, name="bindr")
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        self.http = AuthorizedSession(credentials)

    def verify(self, token):
        from firebase_admin import auth
        try:
            return auth.verify_id_token(token, app=self.app, check_revoked=True)
        except (auth.InvalidIdTokenError, auth.ExpiredIdTokenError, auth.RevokedIdTokenError, auth.UserDisabledError) as exc:
            raise InvalidIdentity() from exc
        except Exception as exc:
            raise IdentityUnavailable() from exc

    def user(self, uid):
        # Python Admin SDK does not expose enrolled MFA factors. Use the documented
        # Admin accounts:lookup REST API with the Cloud Run service identity.
        try:
            response = self.http.post(
                f"https://identitytoolkit.googleapis.com/v1/projects/{settings.FIREBASE_PROJECT_ID}/accounts:lookup",
                json={"localId": [uid]}, timeout=10,
            )
            if not response.ok:
                raise IdentityUnavailable()
            users = response.json().get("users", [])
            if len(users) != 1 or users[0].get("localId") != uid:
                raise InvalidIdentity()
            return users[0]
        except (IdentityUnavailable, InvalidIdentity):
            raise
        except Exception as exc:
            raise IdentityUnavailable() from exc

    def revoke(self, uid):
        from firebase_admin import auth
        try:
            auth.revoke_refresh_tokens(uid, app=self.app)
        except Exception as exc:
            raise IdentityUnavailable() from exc


    def delete(self, uid):
        from firebase_admin import auth
        try:
            auth.delete_user(uid, app=self.app)
        except auth.UserNotFoundError:
            return  # Idempotent retry after a lost acknowledgement.
        except Exception as exc:
            raise IdentityUnavailable() from exc


@lru_cache(maxsize=1)
def get_identity_provider():
    try:
        return GoogleIdentity()
    except Exception as exc:
        raise IdentityUnavailable() from exc
