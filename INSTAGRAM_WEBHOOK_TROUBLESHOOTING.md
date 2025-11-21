# Instagram Webhook & Messaging Troubleshooting Guide

## Common Issues and Solutions

### Issue 1: "User Not Found" Error (Error Code 100, Subcode 2534014)

**Error Message**: `Der gesuchte Nutzer wurde nicht gefunden` (User not found)

**Causes & Solutions**:

#### Solution 1: Check API Endpoint
❌ **Wrong**: `https://graph.instagram.com/v21.0/me/messages`
✅ **Correct**: `https://graph.facebook.com/v21.0/me/messages`

Instagram messaging uses the **Facebook Graph API**, not graph.instagram.com!

**Fix in n8n**:
1. Go to "Send to Instagram" node
2. Check the URL field
3. Ensure it's: `https://graph.facebook.com/v21.0/me/messages`
4. NOT: `https://graph.instagram.com/v21.0/me/messages`

#### Solution 2: Wrong Page Access Token
You might be using an Instagram User token instead of a Facebook Page token.

**Get the correct token**:
```bash
# 1. Go to Graph API Explorer: https://developers.facebook.com/tools/explorer/
# 2. Select your Facebook PAGE (not Instagram account)
# 3. Add permissions:
#    - pages_messaging
#    - pages_manage_metadata
#    - instagram_basic
#    - instagram_manage_messages
# 4. Generate Access Token
# 5. Exchange for long-lived token:

curl -X GET "https://graph.facebook.com/v21.0/oauth/access_token?grant_type=fb_exchange_token&client_id=YOUR_APP_ID&client_secret=YOUR_APP_SECRET&fb_exchange_token=SHORT_LIVED_TOKEN"
```

#### Solution 3: Instagram Account Not Linked to Page
The Instagram Business account must be connected to your Facebook Page.

**Check connection**:
```bash
# Get your page ID and check Instagram connection
curl "https://graph.facebook.com/v21.0/me/accounts?access_token=YOUR_PAGE_TOKEN"

# Check if Instagram is connected
curl "https://graph.facebook.com/v21.0/YOUR_PAGE_ID?fields=instagram_business_account&access_token=YOUR_PAGE_TOKEN"
```

**Expected response**:
```json
{
  "instagram_business_account": {
    "id": "17841477683552925"
  }
}
```

If no `instagram_business_account` field, your Instagram isn't linked!

**Fix**:
1. Go to Facebook Page Settings
2. Instagram → Connect Account
3. Login to your Instagram Business account
4. Authorize the connection

---

### Issue 2: Webhooks Not Triggering

**Symptom**: Test user sends DM but n8n webhook doesn't receive anything.

#### Checklist:

##### 1. Verify Webhook Subscription

**Check in Meta Developer Console**:
```
1. Go to: https://developers.facebook.com/apps/YOUR_APP_ID/webhooks/
2. Select "Instagram" from dropdown
3. Check subscription status
4. Ensure these fields are checked:
   ✅ messages
   ✅ messaging_postbacks
```

**Verify via API**:
```bash
# Check app subscriptions
curl -X GET "https://graph.facebook.com/v21.0/YOUR_APP_ID/subscriptions?access_token=YOUR_APP_TOKEN"
```

**Expected response**:
```json
{
  "data": [
    {
      "object": "instagram",
      "callback_url": "https://your-n8n.app.n8n.cloud/webhook/instagram-dm",
      "active": true,
      "fields": [
        {
          "name": "messages",
          "version": "v21.0"
        }
      ]
    }
  ]
}
```

##### 2. Test Webhook Verification

Your webhook must respond to Meta's verification challenge:

**Test manually**:
```bash
# This should return the challenge number
curl "https://your-n8n.app.n8n.cloud/webhook/instagram-dm?hub.mode=subscribe&hub.verify_token=your_verify_token_12345&hub.challenge=1234567890"

# Expected response: 1234567890
```

If this fails:
- n8n workflow isn't active
- Verify token doesn't match
- Webhook path is wrong

##### 3. Subscribe Page to App

**CRITICAL**: Your Facebook Page must be subscribed to your app's webhooks!

```bash
# Subscribe page to app webhooks
curl -X POST "https://graph.facebook.com/v21.0/YOUR_PAGE_ID/subscribed_apps?subscribed_fields=messages,messaging_postbacks&access_token=YOUR_PAGE_TOKEN"
```

**Expected response**:
```json
{
  "success": true
}
```

**Verify subscription**:
```bash
# Check if page is subscribed
curl "https://graph.facebook.com/v21.0/YOUR_PAGE_ID/subscribed_apps?access_token=YOUR_PAGE_TOKEN"
```

**Expected response**:
```json
{
  "data": [
    {
      "id": "YOUR_APP_ID",
      "name": "Your App Name",
      "subscribed_fields": [
        "messages",
        "messaging_postbacks"
      ]
    }
  ]
}
```

**If the `data` array is empty**, your page isn't subscribed! Run the POST command above.

##### 4. Check Test User Permissions

Test users must have specific permissions to trigger webhooks in Development Mode.

**Add test user to app roles**:
```
1. Meta Developers → Your App → Roles → Test Users
2. Create new test user OR add existing
3. Accept permissions for the test user
4. Login to Instagram with test account
5. Send DM to your business page
```

**Important**: The test user's Instagram account must:
- ✅ Be logged in
- ✅ Have access to your app
- ✅ Send DM to the correct business page
- ✅ Business page must be linked to Facebook page

##### 5. Check n8n Webhook Configuration

**In your n8n workflow**:
1. "Instagram Webhook" node must be **Active** (green toggle)
2. Webhook path: `instagram-dm` (not `/instagram-dm`)
3. Response mode: `responseNode`
4. HTTP Method: Both GET and POST allowed

**Test in n8n**:
1. Go to workflow → Click "Instagram Webhook" node
2. Copy the webhook URL shown
3. Test it with curl:
```bash
# Test GET (verification)
curl "https://your-n8n.app.n8n.cloud/webhook/instagram-dm?hub.mode=subscribe&hub.verify_token=your_verify_token_12345&hub.challenge=12345"

# Should return: 12345
```

##### 6. Check Meta App Status

**App must be in correct mode**:
```
Meta Developers → Your App → Settings → Basic

Check:
- App Mode: Development (for testing with test users)
- App is NOT in Live Mode (can't receive webhooks if in Review)
```

##### 7. Monitor Webhook Deliveries

**Check if Meta is sending webhooks**:
```
1. Meta Developers → Your App → Webhooks
2. Select Instagram
3. Click "Test" button
4. Send test event
5. Check delivery status
```

**Common errors**:
- **Connection refused**: n8n webhook URL is wrong or inactive
- **Timeout**: n8n taking too long to respond
- **401/403**: Authorization issue
- **404**: Wrong webhook path

---

### Issue 3: Wrong User ID in Response

**Error**: Sending to `17841477683552925` but user not found

**Cause**: Using Instagram Business Account ID instead of user IGSID

**Solution**: Use the sender ID from the webhook payload

**In n8n "Send to Instagram" node**:
```javascript
// ✅ CORRECT - Use sender_id from webhook
{
  "recipient": {
    "id": $node['Extract Message Data'].json.sender_id  // This is the IGSID
  },
  "message": {
    "text": "Your response here"
  }
}

// ❌ WRONG - Don't use your business account ID
{
  "recipient": {
    "id": "17841477683552925"  // This is YOUR account, not the user!
  }
}
```

**Debug**: Check what ID is being extracted:
1. In n8n, check "Extract Message Data" node output
2. Look at `sender_id` field
3. It should be a long numeric ID (different from your business account ID)

---

## Complete Setup Verification Script

Run this script to verify everything is configured correctly:

```bash
#!/bin/bash

# Configuration
APP_ID="your_app_id"
APP_SECRET="your_app_secret"
PAGE_ID="your_page_id"
PAGE_TOKEN="your_page_access_token"
APP_TOKEN="your_app_access_token"
WEBHOOK_URL="https://your-n8n.app.n8n.cloud/webhook/instagram-dm"
VERIFY_TOKEN="your_verify_token_12345"

echo "=== Instagram Webhook Setup Verification ==="
echo ""

# 1. Check webhook verification
echo "1. Testing webhook verification..."
curl -s "$WEBHOOK_URL?hub.mode=subscribe&hub.verify_token=$VERIFY_TOKEN&hub.challenge=12345"
echo ""
echo ""

# 2. Check app subscriptions
echo "2. Checking app webhook subscriptions..."
curl -s "https://graph.facebook.com/v21.0/$APP_ID/subscriptions?access_token=$APP_TOKEN" | jq .
echo ""

# 3. Check page subscription to app
echo "3. Checking if page is subscribed to app..."
curl -s "https://graph.facebook.com/v21.0/$PAGE_ID/subscribed_apps?access_token=$PAGE_TOKEN" | jq .
echo ""

# 4. Check Instagram connection
echo "4. Checking Instagram Business Account connection..."
curl -s "https://graph.facebook.com/v21.0/$PAGE_ID?fields=instagram_business_account&access_token=$PAGE_TOKEN" | jq .
echo ""

# 5. Get Instagram account details
echo "5. Getting Instagram account details..."
IG_ACCOUNT_ID=$(curl -s "https://graph.facebook.com/v21.0/$PAGE_ID?fields=instagram_business_account&access_token=$PAGE_TOKEN" | jq -r '.instagram_business_account.id')
curl -s "https://graph.facebook.com/v21.0/$IG_ACCOUNT_ID?fields=id,username,name&access_token=$PAGE_TOKEN" | jq .
echo ""

echo "=== Verification Complete ==="
```

Save as `verify_instagram_setup.sh` and run:
```bash
chmod +x verify_instagram_setup.sh
./verify_instagram_setup.sh
```

---

## Quick Fix Checklist

If webhooks aren't working, check these in order:

- [ ] n8n workflow is **Active** (green toggle)
- [ ] Webhook URL in Meta matches n8n URL exactly
- [ ] Verify token in Meta matches n8n workflow
- [ ] Webhook verification test returns challenge number
- [ ] Facebook Page is connected to Instagram Business account
- [ ] **Page is subscribed to app** (most common issue!)
- [ ] Test user is added to app roles
- [ ] App is in Development mode
- [ ] Using correct endpoint: `graph.facebook.com` (not `graph.instagram.com`)
- [ ] Using Page Access Token (not User Token)
- [ ] Token has correct permissions (`pages_messaging`, `instagram_manage_messages`)

---

## Still Not Working? Debug Steps

### Step 1: Test with Meta's Test Tool

```
1. Go to: https://developers.facebook.com/tools/webhooks/
2. Select your app
3. Select Instagram
4. Click "Test" button
5. Choose "Messages" event
6. Click "Send to My Server"
```

If this works but real DMs don't:
- ✅ Webhook subscription is correct
- ❌ Problem is with test user or page connection

If this doesn't work:
- ❌ Webhook subscription has issues
- Check n8n logs for errors

### Step 2: Check n8n Executions

```
1. Go to n8n Cloud
2. Click "Executions" in sidebar
3. Look for failed executions
4. Check error messages
```

Common errors:
- `Query parameter missing`: Verification issue
- `No execution found`: Webhook isn't being triggered
- `404`: Wrong path in n8n

### Step 3: Monitor in Real-Time

**Terminal 1** - Watch n8n executions:
```bash
# Use n8n CLI if installed
n8n webhook --tunnel
```

**Terminal 2** - Send test message:
```bash
# Use a script to trigger webhook
curl -X POST "$WEBHOOK_URL" \
  -H "Content-Type: application/json" \
  -d '{
    "object": "instagram",
    "entry": [{
      "messaging": [{
        "sender": {"id": "test_user_123"},
        "recipient": {"id": "your_page_id"},
        "timestamp": 1234567890,
        "message": {
          "mid": "test_mid",
          "text": "Hello"
        }
      }]
    }]
  }'
```

If this triggers n8n but real DMs don't:
- ❌ Page isn't subscribed to app webhooks
- ❌ Test user doesn't have permissions

---

## Most Common Solution

**90% of "webhook not working" issues are solved by**:

```bash
# Subscribe your page to app webhooks
curl -X POST "https://graph.facebook.com/v21.0/YOUR_PAGE_ID/subscribed_apps?subscribed_fields=messages,messaging_postbacks&access_token=YOUR_PAGE_TOKEN"
```

Check if it worked:
```bash
curl "https://graph.facebook.com/v21.0/YOUR_PAGE_ID/subscribed_apps?access_token=YOUR_PAGE_TOKEN"
```

You should see your app ID in the response!

---

## Contact Points for Support

1. **n8n Community**: https://community.n8n.io/
2. **Meta Developer Support**: https://developers.facebook.com/support/
3. **Check Render Logs**: Dashboard → Your Service → Logs

---

**Last Updated**: 2025-01-19
**Tested With**: n8n Cloud, Meta API v21.0, Instagram Messaging API
