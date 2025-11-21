# Free Deployment Options (NO Credit Card Required)

This guide covers deployment platforms that don't require a credit card to get started.

## Recommended: Render.com

**Why Render?**
- NO credit card required for free tier
- 750 free hours/month (enough for 24/7 operation)
- Free TLS/SSL certificate
- Automatic deploys from GitHub
- PostgreSQL database option (free tier available)

**Limitations:**
- Service spins down after 15 minutes of inactivity
- First request after spin-down takes 30-60 seconds (cold start)
- 512 MB RAM, shared CPU on free tier

### Deploy to Render (Step-by-Step)

#### 1. Push Code to GitHub

Your repository should already be on GitHub. If not:

```bash
# If you need to push to your own GitHub:
git remote add github https://github.com/YOUR_USERNAME/AI_Microservices.git
git push -u github main
```

#### 2. Create Render Account

1. Go to https://render.com
2. Sign up with GitHub (recommended) or email
3. **NO credit card needed**

#### 3. Create New Web Service

1. Click "New +" > "Web Service"
2. Connect your GitHub repository
3. Select your `AI_Microservices` repository
4. Configure:

   **Basic Settings:**
   - Name: `ecommerce-dm-service`
   - Region: `Frankfurt (EU)` (closest to Egypt)
   - Branch: `main` or your branch name
   - Root Directory: leave empty
   - Runtime: `Python 3`

   **Build & Start Commands:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

   **Instance Type:**
   - Select: `Free`

5. Click "Create Web Service"

#### 4. Add Environment Variables

After service is created:

1. Go to your service dashboard
2. Click "Environment" in left sidebar
3. Add these variables:

```
DATABASE_URL = postgresql+asyncpg://user:pass@db.supabase.co:5432/postgres
API_KEY = your-secure-api-key-32-characters-minimum
DEBUG = false
RATE_LIMIT_PER_MINUTE = 100
```

4. Click "Save Changes"
5. Service will automatically redeploy

#### 5. Get Your URL

After deployment completes:
- Your URL: `https://ecommerce-dm-service.onrender.com`
- Health check: `https://ecommerce-dm-service.onrender.com/health`

#### 6. Keep Service Awake (Optional)

Free tier services sleep after 15 min of inactivity. To prevent this:

**Option 1: External Ping Service (Recommended)**
- Use https://uptimerobot.com (free)
- Create monitor for your `/health` endpoint
- Set interval to 14 minutes

**Option 2: Render Cron Job**
Add to your service (costs build minutes):
```yaml
# In render.yaml
services:
  - type: cron
    name: keep-alive
    runtime: python
    schedule: "*/14 * * * *"
    buildCommand: pip install httpx
    startCommand: python -c "import httpx; httpx.get('https://your-service.onrender.com/health')"
```

### Alternative: Render Blueprint (One-Click Deploy)

If you have `render.yaml` in your repo (already created):

1. Go to Render Dashboard
2. Click "New +" > "Blueprint"
3. Connect your repository
4. Select the repo with `render.yaml`
5. Set environment variables when prompted
6. Click "Apply"

Done! Render reads `render.yaml` and configures everything automatically.

---

## Alternative 2: PythonAnywhere

**Pros:**
- Free tier available
- No credit card required
- Good for Python apps

**Cons:**
- Only 1 free web app
- Limited to specific domains (external API calls restricted)
- 100 CPU seconds per day
- **May have issues calling external APIs (Meta, OpenAI)**

**Not recommended** for this project due to external API restrictions.

---

## Alternative 3: Koyeb

**Pros:**
- Free tier available
- No credit card required initially
- Docker support
- Good performance

**Cons:**
- Limited free tier (2 nano instances)
- May require card after trial

### Deploy to Koyeb

1. Sign up at https://www.koyeb.com
2. Connect GitHub
3. Create new service from your repo
4. Set build and run commands same as Render
5. Add environment variables

---

## Alternative 4: Hugging Face Spaces (Docker)

**Pros:**
- Free tier available
- No credit card
- Good for ML/AI projects

**Cons:**
- Primarily for ML demos
- 16GB storage limit
- May not be ideal for production APIs

### Deploy to HF Spaces

1. Create account at https://huggingface.co
2. Create new Space
3. Select "Docker" as SDK
4. Upload your code
5. Configure Dockerfile

---

## Alternative 5: Google Cloud Run (Free Tier)

**Pros:**
- 2 million requests/month free
- Scales to zero
- Professional infrastructure

**Cons:**
- **Requires credit card** for verification
- Complex setup
- Pay-as-you-go after free tier

---

## Alternative 6: Deta Space

**Pros:**
- Completely free
- No credit card
- Simple deployment

**Cons:**
- Limited to their ecosystem
- May not support all Python packages
- Less control over environment

---

## Comparison Table

| Platform | Credit Card | Free Tier | Cold Start | Best For |
|----------|------------|-----------|------------|----------|
| **Render** | ❌ Not needed | 750 hrs/month | 30-60s | This project |
| Railway | ✅ Required | $5 credit | None | - |
| Fly.io | ✅ Required | Limited | None | - |
| PythonAnywhere | ❌ Not needed | 1 app | N/A | Simple apps |
| Koyeb | ❌ Initially | 2 nano | ~10s | Small apps |
| HF Spaces | ❌ Not needed | Unlimited | Varies | ML demos |
| Google Cloud | ✅ Required | 2M req/mo | ~5s | Production |

---

## Recommended Setup: Render + UptimeRobot

1. **Deploy to Render** (free, no card)
2. **Set up UptimeRobot** (free, keeps service awake)
3. **Use Supabase** for database (free tier, no card for basic)

This combination gives you:
- 24/7 availability
- Zero cold starts (with ping)
- No credit card needed
- Professional infrastructure

---

## Important: Cold Start Handling

Since free tiers have cold starts (service sleeps when idle), your n8n workflow should handle this:

**In your n8n HTTP Request nodes, set:**
- Timeout: 30000 ms (30 seconds) instead of default 10s
- Retry on fail: Yes
- Max retries: 3

This ensures the first request after sleep doesn't fail.

---

## Environment Variables Checklist

Wherever you deploy, set these:

```bash
# Required
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
API_KEY=your-secure-random-key-minimum-32-characters

# Optional (have defaults)
DEBUG=false
RATE_LIMIT_PER_MINUTE=100
DEFAULT_CACHE_TTL_HOURS=24
MAX_CONVERSATION_HISTORY=50
MAX_PRODUCT_SEARCH_RESULTS=5
```

---

## Final Recommendation

**Use Render** for this project:

1. No credit card required
2. Simple GitHub deployment
3. Free tier is sufficient
4. Located in Frankfurt (EU) - good latency to Egypt
5. Automatic HTTPS
6. Easy environment variable management

The cold start issue can be solved with a free monitoring service like UptimeRobot, giving you essentially 24/7 availability at zero cost.
