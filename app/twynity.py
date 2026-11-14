"""Twynity discovery + OAuth 2.0 external-connection routes (Interconnector \u00a710.3).

The OAuth category requires three endpoints (``{provider}`` is
``settings.OAUTH_PROVIDER``):

  GET  /api/v1/auth/{provider}/login?redirect_uri={uri}
       \u2014 start the flow: mint a single-use ``state``, store it with the
       auth\u2019d user/persona, and return the provider authorization URL.

  POST /api/v1/auth/{provider}/token-callback?redirect_uri={uri}&code={code}
       \u2014 Twynity calls this after the provider bounces to ``redirect_uri``.
       It looks the ``state`` back up, exchanges ``code`` for tokens, stores
       them encrypted, and deletes the one-shot session.

  POST /api/v1/auth/{provider}/logout
       \u2014 revoke where supported and delete the stored tokens.

Plus the manifest (declaring ``external_connections.oauth``) and
``/api/v1/external-connection/me`` (connection status).

NOTE on ``redirect_uri`` (\u00a710.3): it is the URI Twynity provides, NOT this
server\u2019s callback. It must EXACTLY match what was registered with the OAuth
provider, or the flow fails silently.
"""

import secrets
import time

import httpx
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.auth import get_identity
from app.config import settings
from app.connection_store import get_active_store


def _provider() -> str:
    return settings.OAUTH_PROVIDER


def _query(request: Request) -> dict:
    return dict(request.query_params)


def _build_authorization_url(state: str, redirect_uri: str) -> str:
    params = {
        "response_type": "code",
        "client_id": settings.OAUTH_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "state": state,
    }
    if settings.OAUTH_SCOPES:
        params["scope"] = settings.OAUTH_SCOPES
    return f"{settings.OAUTH_AUTHORIZE_URL}?{httpx.QueryParams(params)}"


async def _exchange_code(code: str, redirect_uri: str) -> dict:
    """Exchange the authorization code for tokens at the provider token URL."""
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": settings.OAUTH_CLIENT_ID,
        "client_secret": settings.OAUTH_CLIENT_SECRET,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(settings.OAUTH_TOKEN_URL, data=data)
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("message", resp.text)
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=502, detail="Token exchange failed: " + str(detail))
    result = resp.json()
    # Log the token response for debugging
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Token exchange response: {result}")
    logger.info(f"Access token scopes: {result.get('scope', 'N/A')}")
    return result


def register_routes(mcp):
    provider = _provider()

    @mcp.custom_route("/api/v1/.well-known/mcp.json", methods=["GET"])
    async def manifest(request: Request) -> JSONResponse:
        return JSONResponse({
            "name": settings.APP_TITLE,
            "base_url": f"{settings.PUBLIC_URL.rstrip('/')}/mcp",
            "version": settings.APP_VERSION,
            # \u00a710.6 \u2014 declare only the categories this MCP implements.
            "external_connections": {
                "oauth": {"provider": provider}
            },
        })

    @mcp.custom_route(f"/api/v1/auth/{provider}/login", methods=["GET"])
    async def auth_login(request: Request) -> JSONResponse:
        identity = await get_identity(request)
        # Frontend URL: where the user's browser should go after OAuth completes.
        frontend_redirect_uri = _query(request).get("redirect_uri", "").strip()
        if not frontend_redirect_uri:
            return JSONResponse({"detail": "redirect_uri query parameter is required"}, status_code=422)

        # Validate against allowlist
        allowed = [u.strip() for u in settings.FRONTEND_CALLBACK_ALLOWLIST.split(",") if u.strip()]
        if allowed and frontend_redirect_uri not in allowed:
            return JSONResponse(
                {"detail": "redirect_uri not in allowed list"},
                status_code=403,
            )

        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="OAuth storage is not available")
        # Single-use state bound to this user/persona.
        state = secrets.token_urlsafe(32)
        # Store BOTH: the backend's OAUTH_REDIRECT_URI (for token exchange)
        # and the frontend redirect_uri (for post-callback browser redirect).
        await store.save_session(state, {
            "user_id": identity.user_id,
            "persona_id": identity.persona_id,
            "oauth_redirect_uri": settings.OAUTH_REDIRECT_URI,
            "frontend_redirect_uri": frontend_redirect_uri,
        })
        # Build LinkedIn authorization URL with the BACKEND redirect URI.
        auth_url = _build_authorization_url(state, settings.OAUTH_REDIRECT_URI)
        return JSONResponse({
            "authorization_url": auth_url,
            "state": state,
            "redirect_uri": settings.OAUTH_REDIRECT_URI,
        })

    # Direct OAuth callback route for when the provider redirects back
    @mcp.custom_route("/oauth/callback", methods=["GET"])
    async def oauth_callback(request: Request) -> JSONResponse:
        query = _query(request)
        error = query.get("error")
        state = query.get("state", "").strip()

        if error:
            frontend_uri = "unknown"
            if state:
                store = get_active_store()
                if store:
                    session = await store.get_session(state)
                    if session:
                        session_data = session.get("session_data", {})
                        frontend_uri = session_data.get("frontend_redirect_uri", "unknown")
            return JSONResponse({
                "error": error,
                "error_description": query.get("error_description", "Unknown error"),
                "state": state,
                "redirect_uri": frontend_uri,
            }, status_code=400)

        code = query.get("code", "").strip()
        if not code or not state:
            return JSONResponse({"detail": "code and state are required"}, status_code=400)

        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="OAuth storage is not available")

        session = await store.get_session(state)
        if not session:
            return JSONResponse({
                "error": "invalid_state",
                "error_description": "Invalid or expired authorization state.",
            }, status_code=400)

        session_data = session.get("session_data", {})
        oauth_redirect_uri = session_data.get("oauth_redirect_uri", settings.OAUTH_REDIRECT_URI)
        frontend_redirect_uri = session_data.get("frontend_redirect_uri", "")
        user_id = session_data.get("user_id")
        persona_id = session_data.get("persona_id")

        # Single-use: delete immediately
        await store.delete_session(state)

        # Exchange code for tokens
        try:
            token = await _exchange_code(code, oauth_redirect_uri)
        except HTTPException as exc:
            return JSONResponse({"error": exc.detail}, status_code=exc.status_code)

        expires_in = token.get("expires_in")
        expires_at = (time.time() + expires_in) if isinstance(expires_in, (int, float)) else None

        await store.save_token(user_id, persona_id, {
            "access_token": token.get("access_token", ""),
            "refresh_token": token.get("refresh_token", ""),
            "expires_at": expires_at,
        })

        return JSONResponse({
            "connected": True,
            "redirect_uri": frontend_redirect_uri,
            "state": state,
        })

    @mcp.custom_route(f"/api/v1/auth/{provider}/token-callback", methods=["POST"])
    async def auth_token_callback(request: Request) -> JSONResponse:
        identity = await get_identity(request)
        query = _query(request)
        code = query.get("code", "").strip()
        state = query.get("state", "").strip()
        if not code or not state:
            return JSONResponse({"detail": "code and state query parameters are required"}, status_code=422)
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="OAuth storage is not available")
        session = await store.get_session(state)
        if not session:
            return JSONResponse(
                {"detail": "invalid_state", "error": "Invalid or expired authorization state."},
                status_code=400,
            )
        session_data = session.get("session_data", {})
        # Use the stored backend redirect URI (not the frontend one) for token exchange.
        oauth_redirect_uri = session_data.get("oauth_redirect_uri", settings.OAUTH_REDIRECT_URI)
        # Single-use: delete immediately, before the exchange.
        await store.delete_session(state)
        # Attribute the tokens to the identity that initiated the flow.
        user_id = session_data.get("user_id", identity.user_id)
        persona_id = session_data.get("persona_id", identity.persona_id)
        try:
            token = await _exchange_code(code, oauth_redirect_uri)
        except HTTPException as exc:
            return JSONResponse({"detail": exc.detail}, status_code=exc.status_code)
        expires_in = token.get("expires_in")
        expires_at = (time.time() + expires_in) if isinstance(expires_in, (int, float)) else None
        await store.save_token(user_id, persona_id, {
            "access_token": token.get("access_token", ""),
            "refresh_token": token.get("refresh_token", ""),
            "expires_at": expires_at,
        })
        # Return the frontend redirect URI so Twynity can navigate the user there.
        return JSONResponse({
            "connected": True,
            "redirect_uri": session_data.get("frontend_redirect_uri", ""),
        })

    @mcp.custom_route(f"/api/v1/auth/{provider}/logout", methods=["POST"])
    async def auth_logout(request: Request) -> JSONResponse:
        try:
            identity = await get_identity(request)
        except Exception:
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="OAuth storage is not available")
        token = await store.get_token(identity.user_id, identity.persona_id)
        # Best-effort provider-side revoke where the provider supports it.
        if settings.OAUTH_REVOKE_URL and token and token.get("access_token"):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    await client.post(
                        settings.OAUTH_REVOKE_URL,
                        data={
                            "token": token["access_token"],
                            "client_id": settings.OAUTH_CLIENT_ID,
                            "client_secret": settings.OAUTH_CLIENT_SECRET,
                        },
                    )
            except httpx.HTTPError:
                pass  # revocation is best-effort; local deletion always happens
        deleted = await store.delete_token(identity.user_id, identity.persona_id)
        return JSONResponse({"disconnected": deleted})

    @mcp.custom_route("/api/v1/external-connection/me", methods=["GET"])
    async def external_connection_me(request: Request) -> JSONResponse:
        identity = await get_identity(request)
        store = get_active_store()
        if store is None:
            raise HTTPException(status_code=503, detail="OAuth storage is not available")
        connected = await store.public_metadata(identity.user_id, identity.persona_id) is not None
        return JSONResponse({"connected": connected})

    @mcp.custom_route("/api/v1/health", methods=["GET"])
    async def health_status(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})
