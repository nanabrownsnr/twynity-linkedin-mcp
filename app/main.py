"""Compose and expose the FastMCP ASGI application.

Import and register new tools/resources here. Twynity-specific HTTP routes live
in ``twynity.py`` and are separate from FastMCP's JWT-protected MCP transport.
"""

import asyncio
from contextlib import asynccontextmanager, suppress
from logging import getLogger

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers
from fastmcp.server.middleware import Middleware as MCPMiddleware
from fastmcp.server.middleware import MiddlewareContext
from pymongo import AsyncMongoClient
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.auth import get_auth_provider
from app.config import settings
from app.connection_store import OAuthStore, set_active_store
from app.license import license_watcher
from app.twynity import register_routes, _exchange_code
from app.tools.linkedin import register_linkedin_tools
from app.usage import save_usage_report


# --- OAuth Callback Handler ---
async def oauth_callback_handler(request: Request) -> JSONResponse:
    """Direct OAuth callback handler for when LinkedIn redirects back."""
    from app.connection_store import get_active_store

    query = dict(request.query_params)
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

logger = getLogger(__name__)


@asynccontextmanager
async def app_lifespan(server):
    import logging
    logger = logging.getLogger(__name__)

    mongo = None
    task = None
    try:
        logger.info("Initializing MongoDB connection...")
        mongo = AsyncMongoClient(settings.MONGODB_URI, tz_aware=True)
        logger.info("MongoDB connection established")

        logger.info("Setting up OAuthStore...")
        store = OAuthStore(
            mongo[settings.DATABASE_NAME]["oauth_tokens"],
            mongo[settings.DATABASE_NAME]["oauth_sessions"],
            settings.ENCRYPTION_KEY,
            settings.OAUTH_SESSION_TTL_SECONDS,
        )
        await store.setup()
        logger.info("OAuthStore initialized successfully")
        set_active_store(store)

        logger.info("Starting license watcher...")
        task = asyncio.create_task(license_watcher())
        logger.info("Server starting...")
        yield
    except Exception as e:
        logger.error(f"Error during lifespan startup: {e}", exc_info=True)
        raise
    finally:
        logger.info("Cleaning up resources...")
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        set_active_store(None)
        if mongo is not None:
            await mongo.close()
            logger.info("MongoDB connection closed")


logger.info("Initializing FastMCP server...")
try:
    mcp = FastMCP(
        settings.APP_TITLE,
        auth=get_auth_provider(),
        lifespan=app_lifespan,
    )
    logger.info("FastMCP server initialized")

    # Register LinkedIn tools
    logger.info("Registering LinkedIn tools...")
    register_linkedin_tools(mcp)
    logger.info("LinkedIn tools registered")

    # Register middleware
    logger.info("Adding usage tracking middleware...")
    class UsageTrackingMiddleware(MCPMiddleware):
        async def on_call_tool(self, context: MiddlewareContext, call_next):
            try:
                headers = get_http_headers()
                await save_usage_report(
                    method="TOOL_CALL",
                    endpoint=context.message.name,
                    auth_header=headers.get("authorization"),
                )
            except Exception:
                logger.exception("Usage tracking failed — continuing with tool call anyway")

            return await call_next(context)

    mcp.add_middleware(UsageTrackingMiddleware())

    # Register routes
    logger.info("Registering Twynity routes...")
    register_routes(mcp)
    logger.info("Routes registered")

    logger.info("Creating HTTP app...")
    origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
    middleware = [
        Middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["mcp-session-id"],
        )
    ]
    app = mcp.http_app(middleware=middleware)
    logger.info("HTTP app created successfully")

    # Add OAuth callback route to the Starlette app
    app.routes.insert(0, Route("/oauth/callback", oauth_callback_handler, methods=["GET"]))
    logger.info("OAuth callback route registered")
except Exception as e:
    logger.error(f"Failed to initialize server: {e}", exc_info=True)
    raise


origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
middleware = [
    Middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["mcp-session-id"],
    )
]


app = mcp.http_app(middleware=middleware)


if __name__ == "__main__":
    import uvicorn
    import sys

    # Setup basic logging to stderr
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stderr),
            logging.FileHandler('/app/logs/startup.log')
        ]
    )

    logger = logging.getLogger(__name__)
    logger.info("========================================")
    logger.info("Starting LinkedIn MCP Server")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"App Title: {settings.APP_TITLE}")
    logger.info(f"Service ID: {settings.SERVICE_ID}")
    logger.info(f"Public URL: {settings.PUBLIC_URL}")
    logger.info(f"Database Name: {settings.DATABASE_NAME}")
    logger.info(f"MongoDB URI: {settings.MONGODB_URI[:50]}...")
    logger.info(f"OAUTH Provider: {settings.OAUTH_PROVIDER}")
    logger.info(f"OAUTH Client ID: {settings.OAUTH_CLIENT_ID[:5]}...")
    logger.info("========================================")

    try:
        logger.info("Starting Uvicorn server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)
