"""Encrypted MongoDB persistence for OAuth tokens + short-lived OAuth sessions.

Two concerns, one module:

1. **OAuth sessions** (``oauth_sessions``): a single-use ``state`` -> session
   data mapping used to hold the user/persona identity across the redirect
   bounce. Entries are TTL-expired and deleted after the code is exchanged.

2. **OAuth tokens** (``oauth_tokens``): the access/refresh tokens, Fernet-
   encrypted at rest and scoped to the exact ``(user_id, persona_id)`` pair.
   Refresh tokens are never returned by ``public_metadata`` — only a non-secret
   summary (``has_access_token`` / ``has_refresh_token``).
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from bson import ObjectId
from cryptography.fernet import Fernet, InvalidToken
from pymongo import ASCENDING

_active_store: "OAuthStore | None" = None


def set_active_store(store: "OAuthStore | None") -> None:
    """Set the process-scoped store created/closed by the ASGI lifespan."""
    global _active_store
    _active_store = store


def get_active_store() -> "OAuthStore | None":
    return _active_store


class OAuthStore:
    """Store OAuth tokens per ``(user_id, persona_id)`` plus ``state`` sessions."""

    def __init__(self, collection: Any, session_collection: Any, encryption_key: str,
                 session_ttl_seconds: int = 600):
        self.collection = collection
        self.session_collection = session_collection
        self.cipher = Fernet(encryption_key.encode("ascii"))
        self.session_ttl = timedelta(seconds=session_ttl_seconds)

    async def setup(self) -> None:
        """Create uniqueness constraints + the session TTL index at startup."""
        await self.collection.create_index(
            [("user_id", ASCENDING), ("persona_id", ASCENDING)], unique=True
        )
        await self.session_collection.create_index([("state", ASCENDING)], unique=True)
        await self.session_collection.create_index([("expires_at", 1)], expireAfterSeconds=0)

    # ---- OAuth state sessions (oauth_sessions) -----------------------------

    async def save_session(self, state: str, session_data: dict[str, Any]) -> None:
        doc = {
            "state": state,
            "session_data": session_data,
            "created": datetime.now(UTC),
            "expires_at": datetime.now(UTC) + self.session_ttl,
        }
        await self.session_collection.replace_one({"state": state}, doc, upsert=True)

    async def get_session(self, state: str) -> dict[str, Any] | None:
        document = await self.session_collection.find_one({"state": state})
        if not document:
            return None
        if document.get("expires_at") and document["expires_at"] < datetime.now(UTC):
            await self.delete_session(state)
            return None
        return document

    async def delete_session(self, state: str) -> None:
        await self.session_collection.delete_one({"state": state})

    # ---- OAuth tokens (oauth_tokens) ---------------------------------------

    async def save_token(self, user_id: str, persona_id: str, token: dict[str, Any]) -> str:
        """Encrypt the token fields and upsert this user/persona’s OAuth grant."""
        now = datetime.now(UTC)
        encrypted = {
            field: self.cipher.encrypt(str(token[field]).encode("utf-8")).decode("ascii")
            for field in ("access_token", "refresh_token")
            if token.get(field)
        }
        expires_at = token.get("expires_at")
        if isinstance(expires_at, (int, float)):
            expires_at = datetime.fromtimestamp(expires_at, UTC)
        result = await self.collection.update_one(
            {"user_id": user_id, "persona_id": persona_id},
            {
                "$set": {"values": encrypted, "expires_at": expires_at, "modified": now},
                "$setOnInsert": {"created": now},
            },
            upsert=True,
        )
        return str(result.upserted_id) if result.upserted_id else "updated"

    async def get_token(self, user_id: str, persona_id: str) -> dict[str, Any] | None:
        """Read and decrypt the exact identity pair; never search by user alone."""
        document = await self.collection.find_one({"user_id": user_id, "persona_id": persona_id})
        if not document:
            return None
        try:
            values = {
                key: self.cipher.decrypt(value.encode("ascii")).decode("utf-8")
                for key, value in document["values"].items()
            }
        except (InvalidToken, KeyError, TypeError) as exc:
            raise RuntimeError("Stored OAuth token could not be decrypted; check ENCRYPTION_KEY") from exc
        return {"id": str(document.get("_id", ObjectId())), **values}

    async def public_metadata(self, user_id: str, persona_id: str) -> dict[str, Any] | None:
        """Return a non-secret summary — NEVER the raw token values (§11.3)."""
        document = await self.collection.find_one(
            {"user_id": user_id, "persona_id": persona_id},
            {"values.access_token": 1, "values.refresh_token": 1, "created": 1, "modified": 1},
        )
        if not document:
            return None
        values = document.get("values", {})
        return {
            "id": str(document["_id"]),
            "has_access_token": bool(values.get("access_token")),
            "has_refresh_token": bool(values.get("refresh_token")),
        }

    async def delete_token(self, user_id: str, persona_id: str) -> bool:
        result = await self.collection.delete_one({"user_id": user_id, "persona_id": persona_id})
        return result.deleted_count == 1
