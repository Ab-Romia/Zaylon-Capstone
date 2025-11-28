# n8n Workflow for AI E-commerce Assistant

This directory contains the n8n workflow configuration for automating your AI-powered e-commerce customer service on Instagram and WhatsApp.

## 📁 Files

- **`n8n_workflow.json`** - Complete n8n workflow (import this into n8n)
- **`N8N_WORKFLOW_SETUP_GUIDE.md`** - Comprehensive setup guide with all configuration steps

## 🚀 Quick Start

### 1. Deploy Your API First

Before using this workflow, deploy the AI microservices API to Render:

1. Push your code to GitHub
2. Create a new Web Service on Render
3. Configure environment variables (see DEPLOYMENT.md)
4. Deploy and verify health check passes

### 2. Import Workflow to n8n

1. Open your n8n instance
2. Go to Workflows → Add Workflow
3. Click "⋮" menu → "Import from File"
4. Select `n8n_workflow.json`
5. Click "Import"

### 3. Configure Environment Variables

Add these to your n8n environment:

```bash
API_URL=https://your-service.onrender.com
API_KEY=your-super-secret-api-key
INSTAGRAM_ACCESS_TOKEN=your-instagram-token
WHATSAPP_API_URL=https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID
WHATSAPP_ACCESS_TOKEN=your-whatsapp-token
```

### 4. Set Up Credentials

In n8n Credentials, add:
- **OpenAI API** (for AI responses)
- Save as: `openai_api_cred`

### 5. Configure Webhooks

**Instagram:**
- Meta Developer Console → Instagram → Webhooks
- URL: `https://your-n8n.com/webhook/instagram-webhook`
- Subscribe to: `messages`

**WhatsApp:**
- Meta Developer Console → WhatsApp → Configuration
- URL: `https://your-n8n.com/webhook/whatsapp-webhook`
- Subscribe to: `messages`

### 6. Activate Workflow

1. Toggle the workflow to "Active" (top right)
2. Send a test message to your Instagram/WhatsApp
3. Check execution logs

## 📊 What It Does

```
Customer Message (Instagram/WhatsApp)
         ↓
   Fetch Context & History
   Search Products (RAG)
   Classify Intent
         ↓
   Cached Response? → Yes → Use Cache
         ↓ No
   Call OpenAI with Full Context
   Generate Contextual Response
         ↓
   Need to Create Order? → Yes → Create in DB
         ↓
   Store Interaction & Log Analytics
         ↓
   Send Reply to Customer
```

## ✨ Features

- ✅ **Bilingual Support** - Arabic & English
- ✅ **Context-Aware** - Remembers conversation history
- ✅ **RAG-Powered** - Semantic product search
- ✅ **Order Creation** - Complete order flow
- ✅ **Smart Caching** - Reduces AI costs by 40-60%
- ✅ **Multi-Channel** - Instagram DMs & WhatsApp
- ✅ **Analytics** - Logs all interactions
- ✅ **Customer Profiles** - Tracks preferences & history

## 📖 Full Documentation

For complete setup instructions, troubleshooting, and advanced configuration:

👉 **Read [`N8N_WORKFLOW_SETUP_GUIDE.md`](./N8N_WORKFLOW_SETUP_GUIDE.md)**

## 🔧 Quick Test

Test the workflow manually:

```bash
# Test Instagram
curl -X POST https://your-n8n.com/webhook/instagram-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender_id": "123456",
    "sender_username": "test_user",
    "message_text": "I want a red dress",
    "channel": "instagram",
    "timestamp": "2025-11-28T12:00:00Z"
  }'

# Test WhatsApp
curl -X POST https://your-n8n.com/webhook/whatsapp-webhook \
  -H "Content-Type: application/json" \
  -d '{
    "sender_phone": "+201234567890",
    "sender_name": "Test User",
    "text": "أريد فستان أحمر",
    "channel": "whatsapp",
    "timestamp": "2025-11-28T12:00:00Z"
  }'
```

## 🆘 Troubleshooting

**Workflow not receiving messages?**
- Check webhook URLs are correct
- Verify workflow is **activated**
- Check Meta webhook subscriptions

**API calls failing?**
- Verify `API_URL` and `API_KEY`
- Test API manually: `curl https://your-api.com/health`
- Check Render service logs

**AI not responding?**
- Verify OpenAI credentials
- Check API key has credits
- Review execution logs in n8n

**Messages not sending?**
- Verify Instagram/WhatsApp tokens
- Check token permissions
- Test sending manually via Graph API

## 📚 API Endpoints Used

The workflow calls these API endpoints:

1. **POST /n8n/prepare-context-enhanced** - Get full context for AI
2. **POST /n8n/create-order** - Create customer order
3. **POST /n8n/store-interaction** - Store conversation & analytics

See full API documentation at: `https://your-api.com/docs`

## 💰 Cost Estimate

| Component | Monthly Cost |
|-----------|--------------|
| n8n Cloud | $20 or $0 (self-hosted) |
| OpenAI API (GPT-4o-mini) | $5-20 (depends on usage) |
| Meta APIs | $0 (free) |
| **Total** | **$5-40/month** |

**Optimize costs:**
- Enable response caching (already configured)
- Use GPT-4o-mini instead of GPT-4
- Set up rate limiting

## 🎯 Next Steps

1. ✅ Deploy API to Render
2. ✅ Import workflow to n8n
3. ✅ Configure environment variables
4. ✅ Set up Instagram/WhatsApp webhooks
5. ✅ Test with real messages
6. 📊 Monitor analytics dashboard
7. 🔧 Customize AI prompts for your brand
8. 📈 Scale as needed

---

**Ready to automate your e-commerce customer service! 🚀**

For detailed instructions, see: [`N8N_WORKFLOW_SETUP_GUIDE.md`](./N8N_WORKFLOW_SETUP_GUIDE.md)
