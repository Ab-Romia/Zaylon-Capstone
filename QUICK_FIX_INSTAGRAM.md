# Instagram Webhook Quick Fix Guide

## Problem 1: "User Not Found" Error

**Error**: `Der gesuchte Nutzer wurde nicht gefunden` (User not found)

### Fix: Check Your API Endpoint

In your n8n "Send to Instagram" node, the URL MUST be:

```
✅ CORRECT: https://graph.facebook.com/v21.0/me/messages
❌ WRONG:   https://graph.instagram.com/v21.0/me/messages
```

Instagram messaging uses **Facebook Graph API**, not graph.instagram.com!

---

## Problem 2: Webhook Not Triggering

**Symptom**: Test user sends DM but nothing happens in n8n.

### Most Common Fix (90% of cases):

**Your Facebook Page is NOT subscribed to app webhooks!**

Run this command:

```bash
curl -X POST \
  "https://graph.facebook.com/v21.0/YOUR_PAGE_ID/subscribed_apps?subscribed_fields=messages,messaging_postbacks&access_token=YOUR_PAGE_TOKEN"
```

**Replace**:
- `YOUR_PAGE_ID` = Your Facebook Page ID
- `YOUR_PAGE_TOKEN` = Your Page Access Token

**Expected response**:
```json
{
  "success": true
}
```

### Verify it worked:

```bash
curl "https://graph.facebook.com/v21.0/YOUR_PAGE_ID/subscribed_apps?access_token=YOUR_PAGE_TOKEN"
```

You should see your app ID in the response!

---

## Problem 3: Can't Get Page ID or Token

### Get Page ID:

```bash
curl "https://graph.facebook.com/v21.0/me/accounts?access_token=YOUR_USER_TOKEN"
```

### Get Page Access Token:

1. Go to [Graph API Explorer](https://developers.facebook.com/tools/explorer/)
2. Select your **Facebook Page** (not user)
3. Add permissions:
   - `pages_messaging`
   - `pages_manage_metadata`
   - `instagram_basic`
   - `instagram_manage_messages`
4. Click "Generate Access Token"
5. Copy the token

### Exchange for Long-Lived Token (60 days):

```bash
curl "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

---

## Diagnostic Tool

Run this script to automatically check your setup:

```bash
chmod +x check_instagram_setup.sh
./check_instagram_setup.sh
```

It will check:
- ✓ Webhook verification
- ✓ Instagram connection
- ✓ Page subscription to app
- ✓ Token permissions
- ✓ Token expiration

---

## Complete Setup Commands

Copy and paste these commands (replace values):

```bash
# 1. Set your variables
PAGE_ID="your_page_id"
PAGE_TOKEN="your_page_access_token"
APP_ID="your_app_id"
WEBHOOK_URL="https://your-n8n.app.n8n.cloud/webhook/instagram-dm"
VERIFY_TOKEN="your_verify_token_12345"

# 2. Subscribe page to app (MOST IMPORTANT!)
curl -X POST \
  "https://graph.facebook.com/v21.0/$PAGE_ID/subscribed_apps?subscribed_fields=messages,messaging_postbacks&access_token=$PAGE_TOKEN"

# 3. Verify page subscription
curl "https://graph.facebook.com/v21.0/$PAGE_ID/subscribed_apps?access_token=$PAGE_TOKEN"

# 4. Check Instagram connection
curl "https://graph.facebook.com/v21.0/$PAGE_ID?fields=instagram_business_account&access_token=$PAGE_TOKEN"

# 5. Test webhook verification
curl "$WEBHOOK_URL?hub.mode=subscribe&hub.verify_token=$VERIFY_TOKEN&hub.challenge=12345"
# Should return: 12345
```

---

## Test Flow

After setup, test with this flow:

1. **Add test user**:
   - Meta Developers → Roles → Test Users → Add

2. **Login to Instagram with test account**

3. **Find your business page on Instagram**

4. **Send DM**: "Hello"

5. **Check n8n**:
   - Go to n8n Cloud → Executions
   - You should see a new execution
   - Check each node for data

6. **Check Render logs**:
   - Render Dashboard → Your service → Logs
   - Look for `/n8n/prepare-context` requests

---

## Still Not Working?

### Check these in order:

1. [ ] Page subscribed to app webhooks? ← **Most common issue!**
2. [ ] Using `graph.facebook.com` (not `graph.instagram.com`)?
3. [ ] Instagram Business account connected to Facebook Page?
4. [ ] n8n workflow is Active (green toggle)?
5. [ ] Webhook verification returns challenge number?
6. [ ] Test user added to app roles?
7. [ ] Page Access Token has correct permissions?
8. [ ] Token is not expired?

### Debug Commands:

```bash
# Check what n8n is receiving
# Go to n8n → Executions → Click latest execution → Check webhook data

# Check Render microservice
curl https://your-app.onrender.com/health

# Test n8n endpoint directly
curl -X POST "https://your-n8n.app.n8n.cloud/webhook/instagram-dm" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "instagram",
    "entry": [{
      "messaging": [{
        "sender": {"id": "test123"},
        "recipient": {"id": "your_page"},
        "message": {"text": "test"}
      }]
    }]
  }'
```

---

## Get Help

- **Detailed guide**: See `INSTAGRAM_WEBHOOK_TROUBLESHOOTING.md`
- **Run diagnostics**: `./check_instagram_setup.sh`
- **Render logs**: Dashboard → Logs tab
- **n8n logs**: Executions → Click execution → View details

---

## Summary

**The #1 fix that solves most issues**:

```bash
curl -X POST \
  "https://graph.facebook.com/v21.0/YOUR_PAGE_ID/subscribed_apps?subscribed_fields=messages,messaging_postbacks&access_token=YOUR_PAGE_TOKEN"
```

Run this command, then test again. It works in 90% of cases!
