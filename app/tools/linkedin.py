"""LinkedIn MCP tools for interacting with LinkedIn API

Available scopes: openid, profile, email, w_member_social
Endpoints:
- /v2/userinfo (openid) → profile, name, email, picture
- /rest/posts (w_member_social) → create posts
- /rest/documents (w_member_social) → documents
- /rest/videos (w_member_social) → videos
- /rest/images (w_member_social) → images
"""

from starlette.exceptions import HTTPException

from app.auth import get_identity_from_context
from app.connection_store import get_active_store
import httpx


async def linkedin_get_profile() -> dict:
    """Get current user's LinkedIn profile information using OAuth 2.0 userinfo endpoint.

    Returns:
        dict: LinkedIn profile data from /v2/userinfo
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {token['access_token']}",
        }
    ) as client:
        response = await client.get("https://api.linkedin.com/v2/userinfo")
        response.raise_for_status()
        return response.json()


async def linkedin_get_email() -> dict:
    """Get user's LinkedIn email address using OAuth 2.0 userinfo endpoint.

    Returns:
        dict: Email address data
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {token['access_token']}",
        }
    ) as client:
        response = await client.get("https://api.linkedin.com/v2/userinfo")
        response.raise_for_status()
        data = response.json()
        return {"email": data.get("email", "N/A")}


async def linkedin_create_post(text: str) -> dict:
    """Create a new LinkedIn post with the provided text.

    Uses the /rest/posts endpoint which requires w_member_social scope.

    Args:
        text: Post content to publish

    Returns:
        dict: Creation result including post URN
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    async with httpx.AsyncClient(
        base_url="https://api.linkedin.com",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
            "Content-Type": "application/json",
        }
    ) as client:
        response = await client.post(
            "/rest/posts",
            json={
                "author": f"urn:li:person:{token.get('user_id', 'unknown')}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        )
        response.raise_for_status()
        return response.json()


def register_linkedin_tools(mcp):
    """Register LinkedIn tools with the FastMCP server."""
    from fastmcp.tools import ToolResult

    @mcp.tool(
        name="linkedin_get_profile",
        description="Get current user's LinkedIn profile information including name, email, and profile picture URL"
    )
    async def tool_linkedin_get_profile() -> ToolResult:
        """Get current user's LinkedIn profile"""
        data = await linkedin_get_profile()
        return ToolResult(content=[data], structured_content={"profile": data})

    @mcp.tool(
        name="linkedin_get_email",
        description="Get user's LinkedIn email address"
    )
    async def tool_linkedin_get_email() -> ToolResult:
        """Get user's LinkedIn email address"""
        data = await linkedin_get_email()
        return ToolResult(content=[data], structured_content={"email": data})

    @mcp.tool(
        name="linkedin_create_post",
        description="Create a new LinkedIn post with the provided text. The post will be published on the user's LinkedIn profile. Requires w_member_social scope."
    )
    async def tool_linkedin_create_post(text: str) -> ToolResult:
        """Create a new LinkedIn post"""
        data = await linkedin_create_post(text)
        return ToolResult(content=[data], structured_content={"post": data})
