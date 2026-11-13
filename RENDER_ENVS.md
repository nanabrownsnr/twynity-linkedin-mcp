# Environment Variables for Render - Add These FIRST

## 🔴 REQUIRED (Add these now to get deployed)

| Variable | Value | Notes |
|----------|-------|-------|
| `MONGODB_URI` | `mongodb://username:password@mongodb-url:27017/database_name` | Use Render's MongoDB or MongoDB Atlas |
| `ENCRYPTION_KEY` | `your_generated_key_here` | Generate with: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `ACCOUNT_SERVICE_URL` | `https://accounts.twynity.com` | Twynity account service |
| `ACCOUNT_SERVICE_JWKS_ENDPOINT` | `/oauth2/keys` | JWKS endpoint |
| `ACCOUNT_SERVICE_JWKS_CACHE_TTL` | `300` | Cache TTL in seconds |
| `SERVICE_ID` | `your-twynity-service-id` | Your Twynity service ID (from Twynity dashboard) |

## 🟡 OPTIONAL (Can add now or later)

| Variable | Value | Notes |
|----------|-------|-------|
| `LICENSE_KEY` | `your-license-key` | If using Twynity license service |
| `LICENSE_SERVER_BASE_URL` | `https://license.twynity.com` | License server URL |
| `LICENSE_SERVER_JWKS_ENDPOINT` | `/oauth2/keys` | JWKS endpoint |
| `LICENSE_SERVER_ACTIVATION_ENDPOINT` | `/activate` | Activation endpoint |
| `USAGE_REPORT_ENDPOINT` | `https://usage.twynity.com/api/v1/report` | Usage reporting |

## 🟢 TWYNITY OAUTH (Leave EMPTY for now)

| Variable | Value | Notes |
|----------|-------|-------|
| `OAUTH_PROVIDER` | (empty) | Will be `linkedin` after LinkedIn app created |
| `OAUTH_CLIENT_ID` | (empty) | Get from LinkedIn Developer Portal |
| `OAUTH_CLIENT_SECRET` | (empty) | Get from LinkedIn Developer Portal |
| `OAUTH_REDIRECT_URI` | (empty) | Your Render URL after deployment |
| `OAUTH_AUTHORIZE_URL` | (empty) | `https://www.linkedin.com/oauth/v2/authorization` |
| `OAUTH_TOKEN_URL` | (empty) | `https://www.linkedin.com/oauth/v2/accessToken` |
| `OAUTH_REVOKE_URL` | (empty) | `https://www.linkedin.com/oauth/v2/revoke` |
| `OAUTH_SCOPES` | (empty) | `r_liteprofile r_emailaddress w_member_social` |
| `OAUTH_SESSION_TTL_SECONDS` | (empty) | `600` |

## 🟢 GENERAL (Can leave defaults)

| Variable | Value | Notes |
|----------|-------|-------|
| `DATABASE_NAME` | `linkedin_mcp` | Database name (default) |
| `PUBLIC_URL` | `https://linkedin-mcp.onrender.com` | Your Render URL after deployment |
| `ENVIRONMENT` | `production` | Environment |
| `ALLOWED_ORIGINS` | `*` | CORS (default) |

## 📝 Steps

1. **Copy the REQUIRED vars** from the table above
2. **Fill in your values**:
   - MongoDB URI (your MongoDB connection string)
   - ENCRYPTION_KEY (generate with the python command)
   - SERVICE_ID (your Twynity service ID)
3. **Leave the rest EMPTY** for now
4. **Deploy** - it should work without LinkedIn credentials
5. **After LinkedIn app created**, add the OAuth vars

## 🔑 Generate Encryption Key

Run this command to generate your encryption key:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copy the output and paste it as `ENCRYPTION_KEY` in Render.
