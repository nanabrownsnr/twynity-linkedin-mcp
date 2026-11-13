# LinkedIn MCP for Twynity

A production-ready LinkedIn MCP server that integrates with Twynity's OAuth Interconnector. Users authenticate via LinkedIn login and their tokens are securely stored in encrypted MongoDB.

## Features

- ✅ **Twynity OAuth 2.0 Integration** - Uses Twynity Interconnector for authentication
- ✅ **Per-User Token Storage** - Encrypted tokens stored per user/persona pair
- ✅ **Interactive OAuth Flow** - Users login to their own LinkedIn account
- ✅ **LinkedIn API Access** - Full access to LinkedIn's v2 API
- ✅ **Production-Ready** - Docker + Render deployment support
- ✅ **Twynity JWT Authentication** - Persona-Id scoping for user/persona isolation

## Tools Available

| Tool | Description |
|------|-------------|
| `linkedin_get_profile` | Get current user's LinkedIn profile |
| `linkedin_get_email` | Get user's LinkedIn email address |
| `linkedin_search_people` | Search for people by keyword |
| `linkedin_create_post` | Create a new LinkedIn post |
| `linkedin_get_connections` | Get first-degree connections |

## Prerequisites

1. **Python 3.11+** installed
2. **MongoDB instance** for encrypted token storage
3. **Twynity account-service URL** with JWT verification configured
4. **LinkedIn Developer account** (will be created in this guide)

## Quick Start

### Step 1: Create LinkedIn Developer App

1. Go to [LinkedIn Developer Portal](https://www.linkedin.com/developers/apps/)
2. Sign up or log in
3. Click **Create Application**
4. Fill in the details:
   - **Name**: `Twynity LinkedIn MCP`
   - **Description**: `LinkedIn MCP integration for Twynity`
   - **Website**: `http://localhost:3000` (or your Twynity deployment)
   - **Redirect URIs**: `http://localhost:3000/oauth/callback` (for development)
5. Click **Submit**

### Step 2: Configure OAuth Scopes

In the LinkedIn Developer Portal, go to **Authentication** and add these scopes:

- `r_liteprofile` - Read profile info
- `r_emailaddress` - Email address
- `w_member_social` - Post, comment, share

### Step 3: Get OAuth Credentials

After creating the app, you'll get:

- **Client ID** (e.g., `78xyz...`)
- **Client Secret** (e.g., `abcd1234...`)
- **Dashboard URL** (for reference)

### Step 4: Setup the MCP Server

1. **Clone the repository**:
   ```bash
   git clone https://github.com/nanabrownsnr/twynity-mcp-oauth-template.git
   cd twynity-mcp-oauth-template
   ```

2. **Copy the LinkedIn configuration**:
   ```bash
   cp .env.linkedin .env
   ```

3. **Install dependencies**:
   ```bash
   uv sync --locked
   ```

4. **Configure environment variables**:
   Edit `.env` and fill in:
   - `ENCRYPTION_KEY` - Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
   - `OAUTH_CLIENT_ID` - Your LinkedIn Client ID
   - `OAUTH_CLIENT_SECRET` - Your LinkedIn Client Secret
   - `OAUTH_REDIRECT_URI` - Your Twynity deployment URL (e.g., `https://your-twynity-domain/oauth/callback`)
   - `MONGODB_URI` - Your MongoDB connection string
   - `ACCOUNT_SERVICE_URL` - Your Twynity account service URL
   - `SERVICE_ID` - Your Twynity service ID

5. **Generate encryption key**:
   ```bash
   uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

### Step 5: Run the Server

**Development Mode**:
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Docker Mode**:
```bash
docker build -t linkedin-mcp .
docker run -p 8000:8000 \
  -e MONGODB_URI=mongodb://mongo:27017 \
  -e ENCRYPTION_KEY=your_encryption_key_here \
  -e OAUTH_CLIENT_ID=your_client_id \
  -e OAUTH_CLIENT_SECRET=your_client_secret \
  -e OAUTH_REDIRECT_URI=https://your-twynity-domain/oauth/callback \
  linkedin-mcp
```

### Step 6: Deploy to Render

1. Push to GitHub
2. Connect Render as a GitHub repository
3. Select Docker as the platform
4. Set environment variables (same as above)
5. Deploy!

## How It Works

### OAuth Flow

1. **User clicks LinkedIn login** → Twynity calls `/api/v1/auth/linkedin/login`
2. **Returns LinkedIn authorization URL** → User logs in to LinkedIn
3. **LinkedIn redirects to Twynity** → Twynity calls `/api/v1/auth/linkedin/token-callback`
4. **Exchange code for tokens** → Tokens stored encrypted in MongoDB
5. **User can now use LinkedIn tools** → Tokens are automatically refreshed

### Token Storage

- Tokens are encrypted using Fernet symmetric encryption
- Stored in MongoDB `oauth_tokens` collection
- Scoped to `(user_id, persona_id)` pair
- Tokens auto-refresh when expired

### Security

- ✅ JWT verification with Twynity account-service
- ✅ Persona-Id header scoping
- ✅ Encrypted token storage
- ✅ Single-use OAuth states
- ✅ Automatic token refresh

## Testing the MCP

Once deployed, users can:

1. **Authenticate** with LinkedIn via Twynity
2. **Call tools** like:
   - `linkedin_get_profile` - View profile
   - `linkedin_create_post` - Post on LinkedIn
   - `linkedin_search_people` - Find connections
   - `linkedin_get_connections` - List connections

## Troubleshooting

### OAuth callback not working

- Check `OAUTH_REDIRECT_URI` matches exactly what's registered in LinkedIn Developer Portal
- Ensure redirect URI is HTTPS in production

### Token expired

- The MCP automatically refreshes tokens
- If tokens are not refreshing, check `OAUTH_TOKEN_URL` is correct

### MongoDB connection failed

- Verify MongoDB is running and accessible
- Check `MONGODB_URI` is correct

### Permission denied

- Verify OAuth scopes are configured in LinkedIn Developer Portal
- Ensure user has granted all required permissions

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

For issues or questions:
- Check the [Template Guide](docs/TEMPLATE_GUIDE.md)
- Open an issue on GitHub
- Contact Twynity support
