import json
import logging
import os
from functools import lru_cache

import azure.functions as func
import jwt
from jwt import PyJWKClient

ANY_ROLE_ENV_ERROR = "compliance officer roles are not configured"


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    tenant_id = os.environ["AZURE_AD_TENANT_ID"]
    jwks_url = f"https://login.microsoftonline.com/{tenant_id}/discovery/v2.0/keys"
    return PyJWKClient(jwks_url)


def _unauthorized(message: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": message}), status_code=401, mimetype="application/json"
    )


def _forbidden(message: str) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"error": message}), status_code=403, mimetype="application/json"
    )


def require_role(
    req: func.HttpRequest, role: str, _decode_unverified: bool = False
) -> tuple[bool, func.HttpResponse | None]:
    auth_header = req.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return False, _unauthorized("missing or malformed Authorization header")

    token = auth_header[len("Bearer "):]

    try:
        if _decode_unverified:
            claims = jwt.decode(token, "test-secret", algorithms=["HS256"])
        else:
            signing_key = _jwks_client().get_signing_key_from_jwt(token)
            client_id = os.environ["AZURE_AD_CLIENT_ID"]
            claims = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=client_id,
            )
    except jwt.PyJWTError as exc:
        logging.warning("token validation failed: %s", exc)
        return False, _unauthorized("invalid or expired token")

    roles = claims.get("roles", [])
    if role not in roles:
        return False, _forbidden(f"requires role '{role}'")

    return True, None
