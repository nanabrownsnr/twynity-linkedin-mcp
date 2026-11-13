# Deployment Guide: LinkedIn MCP on Render

## ✅ Repository Created & Pushed to GitHub

**Repository**: https://github.com/nanabrownsnr/twynity-linkedin-mcp

## 🚀 Deploy to Render

### Step 1: Create Render Account

1. Go to https://render.com
2. Sign up with GitHub or email
3. Connect your GitHub account

### Step 2: Deploy from GitHub

1. Click **New +** → **Web Service**
2. Connect your GitHub repository: `nanabrownsnr/twynity-linkedin-mcp`
3. Configure the service:

#### Build Settings
- **Name**: `linkedin-mcp`
- **Region**: `Singapore (ap-southeast-1)` (closest to you)
- **Branch**: `master`
- **Runtime**: `Docker`

#### Environment Variables (Required)

Add these environment variables in the **Advanced** → **Environment** section:

```bash
# MongoDB (use Render's managed MongoDB or your own)
MONGODB_URI=mongodb://username:password@mongodb-url:27017/database_name

# Encryption key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=your_generated_encryption_key_here

# LinkedIn OAuth Credentials (will be filled after deployment)
OAUTH_CLIENT_ID=your_linkedin_client_id
OAUTH_CLIENT_SECRET=your_linkedin_client_secret
OAUTH_REDIRECT_URI=https://your-render-app-name.onrender.com/oauth/callback

# Twynity Account Service
ACCOUNT_SERVICE_URL=https://accounts.twynity.com
ACCOUNT_SERVICE_JWKS_ENDPOINT=/oauth2/keys
ACCOUNT_SERVICE_JWKS_CACHE_TTL=300

# License Service (optional - skip if not using)
LICENSE_KEY=
LICENSE_SERVER_BASE_URL=https://license.twynity.com
LICENSE_SERVER_JWKS_ENDPOINT=/oauth2/keys
LICENSE_SERVER_ACTIVATION_ENDPOINT=/activate

# Usage Reporting (optional - skip if not using)
USAGE_REPORT_ENDPOINT=https://usage.twynity.com/api/v1/report

# Public URL (this will be your Render URL)
PUBLIC_URL=https://your-render-app-name.onrender.com

# Environment
ENVIRONMENT=production

# CORS
ALLOWED_ORIGINS=*
```

#### Build Command
```bash
uv sync --locked
```

#### Start Command
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

### Step 3: Deploy

1. Click **Create Web Service**
2. Wait for deployment (5-10 minutes)
3. Once deployed, you'll get a URL like:
   - https://linkedin-mcp.onrender.com

### Step 4: Test Deployment

1. Go to your Render dashboard
2. Click on your service
3. Under **Logs**, check if the server started successfully
4. Test the health endpoint:
   ```bash
   curl https://your-render-app-name.onrender.com/api/v1/health
   ```

## 🔑 Setup LinkedIn Developer Credentials

### Step 1: Get Production Redirect URI

From your Render deployment, you'll have a URL like:
```
https://linkedin-mcp.onrender.com/oauth/callback
```

### Step 2: Create LinkedIn Developer App

1. Go to https://www.linkedin.com/developers/apps/
2. Click **Create Application**
3. Fill in:
   - **Name**: `Twynity LinkedIn MCP`
   - **Description**: `LinkedIn MCP integration for Twynity`
   - **Website**: `https://linkedin-mcp.onrender.com`
   - **Redirect URIs**: `https://linkedin-mcp.onrender.com/oauth/callback`
4. Click **Submit**

### Step 3: Configure Scopes

In the **Authentication** section, add these OAuth scopes:
- `r_liteprofile` - Read profile info
- `r_emailaddress` - Email address
- `w_member_social` - Post, comment, share

### Step 4: Get Credentials

After creating the app, you'll receive:
- **Client ID** (starts with `78`)
- **Client Secret** (starts with `abcd`)

Save these - you'll need them in Render environment variables!

### Step 5: Update Render Environment Variables

1. Go to Render Dashboard → Your Service → **Environment**
2. Update these variables:
   - `OAUTH_CLIENT_ID`: Your LinkedIn Client ID
   - `OAUTH_CLIENT_SECRET`: Your LinkedIn Client Secret
   - `OAUTH_REDIRECT_URI`: `https://linkedin-mcp.onrender.com/oauth/callback`
   - `PUBLIC_URL`: `https://linkedin-mcp.onrender.com`

3. Click **Apply Changes** (this will restart the service)

## 📊 Verification Checklist

- [ ] Render deployment successful
- [ ] Health endpoint responds (200 OK)
- [ ] LinkedIn Developer app created
- [ ] Redirect URI configured in LinkedIn
- [ ] OAuth scopes added
- [ ] Client ID and Secret obtained
- [ ] Environment variables updated in Render
- [ ] Service restarted successfully

## 🔍 Monitoring

### Check Logs
- Go to Render Dashboard → Your Service → **Logs**
- Look for errors during deployment
- Monitor for OAuth errors in production

### Health Check
```bash
curl https://linkedin-mcp.onrender.com/api/v1/health
```

Expected response:
```json
{"status": "ok"}
```

## 🚀 Next Steps After Deployment

1. **Test OAuth Flow**:
   - Connect LinkedIn in Twynity
   - Verify authentication works
   - Check MongoDB for encrypted tokens

2. **Monitor MongoDB**:
   - Check your MongoDB instance
   - Verify tokens are being stored correctly
   - Monitor for token refreshes

3. **Set Up Monitoring**:
   - Enable Render logs
   - Set up error alerts
   - Monitor response times

## 🐛 Troubleshooting

### Deployment Fails
- Check build logs in Render
- Verify Dockerfile is correct
- Ensure all environment variables are set

### OAuth Callback Not Working
- Verify `OAUTH_REDIRECT_URI` matches exactly what's in LinkedIn
- Check if Render URL is HTTPS (required for LinkedIn)
- Ensure redirect URI is publicly accessible

### Token Storage Issues
- Verify MongoDB connection string
- Check encryption key is set
- Ensure user has Persona-Id in requests

### Module Import Errors
- Check `uv.lock` is included in repository
- Verify all dependencies are in `pyproject.toml`
- Check Python version compatibility (3.11+)

## 📚 Additional Resources

- [Render Deployment Docs](https://render.com/docs)
- [LinkedIn API Docs](https://learn.microsoft.com/en-us/linkedin/shared/api-guide/concepts)
- [Twynity Interconnector](https://docs.twynity.com/interconnector)
- [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)

## ✅ Done!

Your LinkedIn MCP is now deployed and ready for production use!
