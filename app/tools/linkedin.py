"""LinkedIn MCP tools for interacting with LinkedIn API

Available scopes: openid, profile, email, w_member_social
Endpoints:
- /v2/userinfo (openid) → profile, name, email, picture
- /rest/posts (w_member_social) → create/delete/update posts
- /rest/reactions (w_member_social) → create/delete reactions
- /rest/images (w_member_social) → upload images
- /rest/videos (w_member_social) → upload videos
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


async def linkedin_delete_post(urn: str) -> dict:
    """Delete a LinkedIn post.

    Args:
        urn: The URN of the post to delete (e.g., "urn:li:ugcPost:123456")

    Returns:
        dict: Deletion confirmation
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
        response = await client.delete(
            f"/rest/posts/{urn}"
        )
        response.raise_for_status()
        return response.json()


async def linkedin_update_post(urn: str, text: str) -> dict:
    """Update an existing LinkedIn post.

    Args:
        urn: The URN of the post to update
        text: New post content

    Returns:
        dict: Updated post data
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
        response = await client.put(
            f"/rest/posts/{urn}",
            json={
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": text
                        },
                        "shareMediaCategory": "NONE"
                    }
                }
            }
        )
        response.raise_for_status()
        return response.json()


async def linkedin_create_reaction(urn: str, reaction_type: str = "LIKE") -> dict:
    """Create a reaction (like) on a post or comment.

    Args:
        urn: The URN of the post or comment to react to
        reaction_type: "LIKE", "EMPATHY", "HEART", or "THANKS"

    Returns:
        dict: Reaction creation result
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
            f"/rest/reactions/{urn}",
            json={
                "actor": f"urn:li:person:{token.get('user_id', 'unknown')}",
                "reactionType": reaction_type
            }
        )
        response.raise_for_status()
        return response.json()


async def linkedin_delete_reaction(urn: str) -> dict:
    """Delete a reaction from a post or comment.

    Args:
        urn: The URN of the post or comment

    Returns:
        dict: Reaction deletion confirmation
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
        }
    ) as client:
        response = await client.delete(
            f"/rest/reactions/{urn}"
        )
        response.raise_for_status()
        return response.json()


async def linkedin_upload_image(text: str, image_url: str) -> dict:
    """Create a post with an image.

    Args:
        text: Post content
        image_url: URL of the image to upload

    Returns:
        dict: Post creation result with image media
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
                        "shareMediaCategory": "IMAGE",
                        "shareMedia": {
                            "media": [
                                {
                                    "description": "Uploaded via LinkedIn MCP",
                                    "mediaCategory": "IMAGE",
                                    "title": "Image from MCP",
                                    "status": "READY_TO_UPLOAD",
                                    "uploadStartUrl": {
                                        "action": "INITIALIZE_UPLOAD",
                                        "url": image_url
                                    }
                                }
                            ]
                        }
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        )
        response.raise_for_status()
        return response.json()


async def linkedin_upload_video(text: str, video_url: str) -> dict:
    """Create a post with a video.

    Args:
        text: Post content
        video_url: URL of the video to upload

    Returns:
        dict: Post creation result with video media
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
                        "shareMediaCategory": "VIDEO",
                        "shareMedia": {
                            "media": [
                                {
                                    "description": "Uploaded via LinkedIn MCP",
                                    "mediaCategory": "VIDEO",
                                    "title": "Video from MCP",
                                    "status": "READY_TO_UPLOAD",
                                    "uploadStartUrl": {
                                        "action": "INITIALIZE_UPLOAD",
                                        "url": video_url
                                    }
                                }
                            ]
                        }
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
        )
        response.raise_for_status()
        return response.json()


# ============================================================================
# Organization Management Tools (Community Management API)
# Requires: w_organization_social, r_organization_social scopes
# ============================================================================


async def linkedin_list_organizations() -> dict:
    """List all organizations the user is a member of.

    Uses the /organizations endpoint from Community Management API.

    Returns:
        dict: List of organizations
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
        }
    ) as client:
        response = await client.get("/organizations", params={"q": "v1:memberships"})
        response.raise_for_status()
        return response.json()


async def linkedin_get_organization(organization_id: str) -> dict:
    """Get detailed information about a specific organization.

    Args:
        organization_id: Organization ID or urn (e.g., "urn:li:organization:123456")

    Returns:
        dict: Organization details including name, industry, size, website
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    # Normalize the org ID to full URN format if needed
    if not organization_id.startswith("urn:li:organization:"):
        org_urn = f"urn:li:organization:{organization_id}"
    else:
        org_urn = organization_id

    async with httpx.AsyncClient(
        base_url="https://api.linkedin.com",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
        }
    ) as client:
        response = await client.get(f"/organizations/{org_urn}")
        response.raise_for_status()
        return response.json()


async def linkedin_get_post(post_urn: str) -> dict:
    """Get details of a specific LinkedIn post.

    Args:
        post_urn: The URN of the post (e.g., "urn:li:ugcPost:123456")

    Returns:
        dict: Post details including commentary, media, author, likes, comments
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
        }
    ) as client:
        response = await client.get(f"/posts/{post_urn}")
        response.raise_for_status()
        return response.json()


async def linkedin_list_posts(author: str, count: int = 10) -> dict:
    """List recent posts from a specific author (person or organization).

    Args:
        author: Author identifier (person ID or org ID)
        count: Number of posts to retrieve (default 10)

    Returns:
        dict: List of posts
    """
    identity = await get_identity_from_context()
    store = get_active_store()
    if store is None:
        raise HTTPException(status_code=503, detail="OAuth storage is not available")

    token = await store.get_token(identity.user_id, identity.persona_id)
    if not token or not token.get("access_token"):
        raise HTTPException(status_code=401, detail="LinkedIn connection not authenticated")

    # Normalize to full URN if needed
    if not author.startswith("urn:"):
        author = f"urn:li:person:{author}"

    async with httpx.AsyncClient(
        base_url="https://api.linkedin.com",
        headers={
            "Authorization": f"Bearer {token['access_token']}",
            "X-Restli-Protocol-Version": "2.0.0",
        }
    ) as client:
        response = await client.get(
            "/posts",
            params={
                "q": "feedby",
                "author": author,
                "count": count,
            }
        )
        response.raise_for_status()
        return response.json()


async def linkedin_get_member_urn() -> dict:
    """Get the current user's LinkedIn member URN.

    Returns:
        dict: Member URN (e.g., "urn:li:person:123456")
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
        # The member URN is constructed from the person ID
        person_id = data.get("sub", "unknown")
        return {
            "member_urn": f"urn:li:person:{person_id}",
            "person_id": person_id,
            "email": data.get("email", "N/A"),
        }


async def linkedin_generic_api_request(
    endpoint: str,
    method: str = "GET",
    params: dict | None = None,
    body: dict | None = None,
) -> dict:
    """Make a generic API request to any LinkedIn endpoint.

    This is a catch-all tool for when the user needs to access a LinkedIn
    endpoint that doesn't have a dedicated tool.

    Args:
        endpoint: API path (e.g., "/rest/posts", "/v2/me")
        method: HTTP method (GET, POST, PUT, DELETE)
        params: Query parameters as dict
        body: Request body as dict

    Returns:
        dict: API response
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
        if method.upper() == "GET":
            response = await client.get(endpoint, params=params)
        elif method.upper() == "POST":
            response = await client.post(endpoint, params=params, json=body)
        elif method.upper() == "PUT":
            response = await client.put(endpoint, params=params, json=body)
        elif method.upper() == "DELETE":
            response = await client.delete(endpoint, params=params)
        else:
            raise HTTPException(status_code=422, detail=f"Unsupported method: {method}")

        response.raise_for_status()
        try:
            return response.json()
        except Exception:
            return {"raw_response": response.text}


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
        description="Create a new LinkedIn post with the provided text. The post will be published on the user's LinkedIn profile."
    )
    async def tool_linkedin_create_post(text: str) -> ToolResult:
        """Create a new LinkedIn post"""
        data = await linkedin_create_post(text)
        return ToolResult(content=[data], structured_content={"post": data})

    @mcp.tool(
        name="linkedin_delete_post",
        description="Delete a LinkedIn post by its URN. Requires w_member_social scope."
    )
    async def tool_linkedin_delete_post(urn: str) -> ToolResult:
        """Delete a LinkedIn post"""
        data = await linkedin_delete_post(urn)
        return ToolResult(content=[data], structured_content={"deleted": True, "urn": urn})

    @mcp.tool(
        name="linkedin_update_post",
        description="Update an existing LinkedIn post by its URN. Requires w_member_social scope."
    )
    async def tool_linkedin_update_post(urn: str, text: str) -> ToolResult:
        """Update an existing LinkedIn post"""
        data = await linkedin_update_post(urn, text)
        return ToolResult(content=[data], structured_content={"updated": True, "urn": urn})

    @mcp.tool(
        name="linkedin_create_reaction",
        description="Create a reaction (like) on a post or comment. Requires w_member_social scope."
    )
    async def tool_linkedin_create_reaction(urn: str, reaction_type: str = "LIKE") -> ToolResult:
        """Create a reaction on a post or comment"""
        data = await linkedin_create_reaction(urn, reaction_type)
        return ToolResult(content=[data], structured_content={"reaction": reaction_type, "urn": urn})

    @mcp.tool(
        name="linkedin_delete_reaction",
        description="Delete a reaction from a post or comment. Requires w_member_social scope."
    )
    async def tool_linkedin_delete_reaction(urn: str) -> ToolResult:
        """Delete a reaction from a post or comment"""
        data = await linkedin_delete_reaction(urn)
        return ToolResult(content=[data], structured_content={"reaction_deleted": True, "urn": urn})

    @mcp.tool(
        name="linkedin_upload_image",
        description="Create a post with an image. Requires w_member_social scope. Provide image URL."
    )
    async def tool_linkedin_upload_image(text: str, image_url: str) -> ToolResult:
        """Create a post with an image"""
        data = await linkedin_upload_image(text, image_url)
        return ToolResult(content=[data], structured_content={"post_created": True, "has_image": True})

    @mcp.tool(
        name="linkedin_upload_video",
        description="Create a post with a video. Requires w_member_social scope. Provide video URL."
    )
    async def tool_linkedin_upload_video(text: str, video_url: str) -> ToolResult:
        """Create a post with a video"""
        data = await linkedin_upload_video(text, video_url)
        return ToolResult(content=[data], structured_content={"post_created": True, "has_video": True})

    # ============================================================================
    # NEW: Organization Management & Account Intelligence Tools
    # ============================================================================

    @mcp.tool(
        name="linkedin_list_organizations",
        description="List all LinkedIn organizations the user is a member of. Requires Community Management API."
    )
    async def tool_linkedin_list_organizations() -> ToolResult:
        """List all organizations the user belongs to"""
        data = await linkedin_list_organizations()
        return ToolResult(content=[data], structured_content={"organizations": data})

    @mcp.tool(
        name="linkedin_get_organization",
        description="Get detailed info about a LinkedIn organization by ID. Requires Community Management API."
    )
    async def tool_linkedin_get_organization(organization_id: str) -> ToolResult:
        """Get organization details"""
        data = await linkedin_get_organization(organization_id)
        return ToolResult(content=[data], structured_content={"organization": data})

    @mcp.tool(
        name="linkedin_get_post",
        description="Get details of a specific LinkedIn post by its URN."
    )
    async def tool_linkedin_get_post(post_urn: str) -> ToolResult:
        """Get post details"""
        data = await linkedin_get_post(post_urn)
        return ToolResult(content=[data], structured_content={"post": data})

    @mcp.tool(
        name="linkedin_list_posts",
        description="List recent posts from a specific author (person or organization). Accepts person/org ID or full URN."
    )
    async def tool_linkedin_list_posts(author: str, count: int = 10) -> ToolResult:
        """List posts from an author"""
        data = await linkedin_list_posts(author, count)
        return ToolResult(content=[data], structured_content={"posts": data})

    @mcp.tool(
        name="linkedin_get_member_urn",
        description="Get the current user's LinkedIn member URN (e.g., urn:li:person:123456)."
    )
    async def tool_linkedin_get_member_urn() -> ToolResult:
        """Get user's member URN"""
        data = await linkedin_get_member_urn()
        return ToolResult(content=[data], structured_content=data)

    @mcp.tool(
        name="linkedin_generic_api_request",
        description="Make any LinkedIn API request. Specify endpoint, method (GET/POST/PUT/DELETE), params dict, and body dict."
    )
    async def tool_linkedin_generic_api_request(
        endpoint: str,
        method: str = "GET",
        params: dict | None = None,
        body: dict | None = None,
    ) -> ToolResult:
        """Generic LinkedIn API call"""
        data = await linkedin_generic_api_request(endpoint, method, params, body)
        return ToolResult(content=[data], structured_content={"response": data})
