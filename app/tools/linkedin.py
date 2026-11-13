"""LinkedIn MCP tools for interacting with LinkedIn API"""

from starlette.exceptions import HTTPException

from app.auth import get_identity_from_context
from app.connection_store import get_active_store
import httpx


async def linkedin_get_profile() -> dict:
    """Get current user's LinkedIn profile information including name, headline, summary, and profile picture URL.

    Returns:
        dict: LinkedIn profile data
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    async with httpx.AsyncClient(
        base_url="https://api.linkedin.com/v2",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "v2"
        }
    ) as client:
        response = await client.get("/me")
        response.raise_for_status()
        return response.json()


async def linkedin_get_email() -> dict:
    """Get user's LinkedIn email address.

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
        base_url="https://api.linkedin.com/v2",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "v2"
        }
    ) as client:
        response = await client.get("/emailAddress")
        response.raise_for_status()
        return response.json()


async def linkedin_search_people(query: str, limit: int = 10) -> dict:
    """Search for people on LinkedIn by keyword.

    Args:
        query: Search query string
        limit: Maximum number of results to return (default: 10)

    Returns:
        dict: Search results with matching profiles
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    async with httpx.AsyncClient(
        base_url="https://api.linkedin.com/v2",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "v2"
        }
    ) as client:
        response = await client.get(f"/search?q={query}&count={limit}")
        response.raise_for_status()
        return response.json()


async def linkedin_create_post(text: str) -> dict:
    """Create a new LinkedIn post with the provided text.

    Args:
        text: Post content to publish

    Returns:
        dict: Creation result including post ID
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    async with httpx.AsyncClient(
        base_url="https://api.linkedin.com/v2",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "v2"
        }
    ) as client:
        response = await client.post(
            "/ugcPosts",
            json={
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {"text": text},
                        "shareMediaCategory": "NONE"
                    }
                }
            }
        )
        response.raise_for_status()
        return response.json()


async def linkedin_get_connections(count: int = 50) -> dict:
    """Get a list of the user's first-degree connections on LinkedIn.

    Args:
        count: Maximum number of connections to return (default: 50)

    Returns:
        dict: List of connections with profile information
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    async with httpx.AsyncClient(
        base_url="https://api.linkedin.com/v2",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
            "LinkedIn-Version": "v2"
        }
    ) as client:
        response = await client.get(f"/connections?count={count}")
        response.raise_for_status()
        return response.json()


def register_linkedin_tools(mcp):
    """Register LinkedIn tools with the FastMCP server."""
    from fastmcp.tools import ToolResult

    @mcp.tool(name="linkedin_get_profile", description="Get current user's LinkedIn profile information including name, headline, summary, and profile picture URL")
    async def tool_linkedin_get_profile() -> ToolResult:
        """Get current user's LinkedIn profile"""
        data = await linkedin_get_profile()
        return ToolResult(content=[data], structured_content={"profile": data})

    @mcp.tool(name="linkedin_get_email", description="Get user's LinkedIn email address")
    async def tool_linkedin_get_email() -> ToolResult:
        """Get user's LinkedIn email address"""
        data = await linkedin_get_email()
        return ToolResult(content=[data], structured_content={"email": data})

    @mcp.tool(
        name="linkedin_search_people",
        description="Search for people on LinkedIn by keyword. Returns a list of matching profiles with name, headline, and profile URL"
    )
    async def tool_linkedin_search_people(query: str, limit: int = 10) -> ToolResult:
        """Search for people on LinkedIn"""
        data = await linkedin_search_people(query, limit)
        return ToolResult(content=[data], structured_content={"search_results": data})

    @mcp.tool(
        name="linkedin_create_post",
        description="Create a new LinkedIn post with the provided text. The post will be published on the user's LinkedIn profile"
    )
    async def tool_linkedin_create_post(text: str) -> ToolResult:
        """Create a new LinkedIn post"""
        data = await linkedin_create_post(text)
        return ToolResult(content=[data], structured_content={"post": data})

    @mcp.tool(
        name="linkedin_get_connections",
        description="Get a list of the user's first-degree connections on LinkedIn"
    )
    async def tool_linkedin_get_connections(count: int = 50) -> ToolResult:
        """Get user's LinkedIn connections"""
        data = await linkedin_get_connections(count)
        return ToolResult(content=[data], structured_content={"connections": data})
