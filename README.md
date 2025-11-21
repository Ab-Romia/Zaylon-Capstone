# E-commerce DM Microservice

AI-powered microservice for Instagram/WhatsApp DM automation for Egyptian e-commerce businesses. Handles Arabic, Franco-Arabic (Arabizi), and English messages.

## Features

- **Multilingual Product Search** - Search products in Arabic (جينز), Franco-Arabic (3ayez ashtry), and English
- **Conversation Context Management** - Full conversation history with cross-channel (Instagram + WhatsApp) linking
- **Intent Classification** - Fast rule-based intent detection with entity extraction
- **Response Caching** - Reduce OpenAI API costs by caching common responses
- **Analytics Dashboard** - Track messages, orders, response times, and AI costs
- **n8n Integration** - Ready-to-use endpoints for n8n workflow integration

## Quick Start

### 1. Clone and Setup

```bash
cd AI_Microservices

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or: venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings:
# - DATABASE_URL (your Supabase/PostgreSQL connection string)
# - API_KEY (generate a secure key)
```

### 3. Setup Database

Run the migration in your PostgreSQL database:

```bash
psql -d your_database -f schema.sql
```

Or via Supabase SQL Editor: copy and paste contents of `schema.sql`.

### 4. Run the Service

```bash
# Development
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

Service will be available at `http://localhost:8000`

API docs: `http://localhost:8000/docs`

## API Endpoints

### Main n8n Integration Endpoints

These are the primary endpoints for n8n workflow integration:

#### POST /n8n/prepare-context

Prepares everything needed before calling OpenAI. Use this as your first HTTP Request in n8n.

```bash
curl -X POST http://localhost:8000/n8n/prepare-context \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "instagram:@ahmed_cairo",
    "message": "3ayez jeans azra2 size 32",
    "channel": "instagram"
  }'
```

Response:
```json
{
  "conversation_history": "CONVERSATION HISTORY:\n[2024-01-15 10:30:00] Customer: Hi\n...",
  "relevant_products": "RELEVANT PRODUCTS:\nProduct 1: Blue Denim Jeans\nPrice: 599.00 EGP\n...",
  "intent_analysis": {
    "intent": "order_intent",
    "confidence": 0.92,
    "entities": {
      "product_name": "jeans",
      "color": "blue",
      "size": "32"
    },
    "skip_ai": false,
    "suggested_response": null
  },
  "cached_response": null,
  "skip_ai": false,
  "customer_metadata": {
    "name": "Ahmed",
    "phone": "+201063790384",
    "total_interactions": 15,
    "preferred_language": "franco-arabic",
    "linked_channels": []
  }
}
```

**Important:** If `skip_ai` is `true`, use `cached_response` directly without calling OpenAI!

#### POST /n8n/store-interaction

Store the complete interaction after AI responds. Use this as your last HTTP Request in n8n.

```bash
curl -X POST http://localhost:8000/n8n/store-interaction \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "instagram:@ahmed_cairo",
    "channel": "instagram",
    "user_message": "3ayez jeans azra2 size 32",
    "ai_response": "Great choice! The Blue Denim Jeans are available in size 32...",
    "intent": "order_intent",
    "action": "request_info",
    "response_time_ms": 1850,
    "ai_tokens_used": 320
  }'
```

### Product Search

```bash
curl -X POST http://localhost:8000/products/search \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "جينز ازرق",
    "limit": 3
  }'
```

### Conversation Context

```bash
# Store message
curl -X POST http://localhost:8000/context/store \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "instagram:@user",
    "channel": "instagram",
    "message": "Hello",
    "direction": "incoming",
    "intent": "greeting"
  }'

# Retrieve history
curl -X GET "http://localhost:8000/context/retrieve?customer_id=instagram:@user&limit=20" \
  -H "X-API-Key: your-api-key"

# Link channels
curl -X POST http://localhost:8000/context/link-channels \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "primary_id": "instagram:@user",
    "secondary_id": "whatsapp:+201234567890"
  }'
```

### Intent Classification

```bash
curl -X POST http://localhost:8000/intent/classify \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "كم سعر الجينز",
    "context": []
  }'
```

### Response Cache

```bash
# Check cache
curl -X POST http://localhost:8000/cache/check \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "max_age_hours": 24
  }'

# Store in cache
curl -X POST http://localhost:8000/cache/store \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hello",
    "response": "Hi! How can I help?",
    "intent": "greeting",
    "ttl_hours": 48
  }'
```

### Analytics

```bash
# Log event
curl -X POST http://localhost:8000/analytics/log \
  -H "X-API-Key: your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "customer_id": "instagram:@user",
    "event_type": "order_created",
    "event_data": {"product": "jeans", "total": 599},
    "response_time_ms": 2000,
    "ai_tokens_used": 400
  }'

# Get dashboard
curl -X GET "http://localhost:8000/analytics/dashboard?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59" \
  -H "X-API-Key: your-api-key"
```

## n8n Workflow Integration

### Modified Workflow Flow

```
Instagram Webhook
      ↓
HTTP Request: POST /n8n/prepare-context
      ↓
IF node: Check if skip_ai == true
      ├─ YES → Use cached_response directly
      └─ NO  → Call OpenAI with enriched context
      ↓
HTTP Request: POST /n8n/store-interaction
      ↓
Send Response to Instagram
```

### n8n HTTP Request Node Configuration

#### Node 1: Prepare Context

- Method: POST
- URL: `https://dm-service-mpjf.onrender.com/n8n/prepare-context`
- Authentication: Header Auth
  - Name: `X-API-Key`
  - Value: `your-api-key`
- Body:
```json
{
  "customer_id": "instagram:{{ $json.sender_id }}",
  "message": "{{ $json.message_text }}",
  "channel": "instagram"
}
```

#### Node 2: IF - Skip AI Check

- Condition: `{{ $json.skip_ai }} equals true`
- True: Use `{{ $json.cached_response }}`
- False: Proceed to OpenAI node

#### Node 3: OpenAI (Modified Prompt)

System prompt should include:
```
You are a helpful e-commerce assistant for an Egyptian clothing store.

{{ $('Prepare Context').item.json.conversation_history }}

{{ $('Prepare Context').item.json.relevant_products }}

Customer Intent: {{ $('Prepare Context').item.json.intent_analysis.intent }}
Customer Language: {{ $('Prepare Context').item.json.customer_metadata.preferred_language }}

Respond appropriately. If customer wants to order, collect: name, phone, address.
```

#### Node 4: Store Interaction

- Method: POST
- URL: `https://dm-service-mpjf.onrender.com/n8n/store-interaction`
- Body:
```json
{
  "customer_id": "instagram:{{ $('Webhook').item.json.sender_id }}",
  "channel": "instagram",
  "user_message": "{{ $('Webhook').item.json.message_text }}",
  "ai_response": "{{ $json.text }}",
  "intent": "{{ $('Prepare Context').item.json.intent_analysis.intent }}",
  "action": "{{ $json.action }}",
  "order_data": {{ $json.order_data || null }},
  "response_time_ms": {{ Date.now() - $('Webhook').item.json.timestamp }},
  "ai_tokens_used": {{ $json.usage.total_tokens || 0 }}
}
```

## Deployment

### Deploy to Render.com (Recommended - NO Credit Card Required)

1. Push code to GitHub
2. Go to https://render.com and sign up (no credit card needed)
3. Click "New +" > "Web Service"
4. Connect your GitHub repository
5. Configure:
   - Name: `ecommerce-dm-service`
   - Region: `Frankfurt (EU)`
   - Runtime: `Python 3`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - Instance Type: `Free`
6. Add environment variables in dashboard:
   - `DATABASE_URL` = your Supabase connection string
   - `API_KEY` = your secure API key
7. Click "Create Web Service"

Your service will be available at: `https://ecommerce-dm-service.onrender.com`

**Note:** Free tier sleeps after 15 min of inactivity. Use https://uptimerobot.com to ping `/health` every 14 minutes.

See `DEPLOYMENT_OPTIONS.md` for more alternatives (Render (deployed), Koyeb, etc.).

### Docker Deployment

```bash
# Build
docker build -t ecommerce-dm-service .

# Run
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://user:pass@host:5432/db" \
  -e API_KEY="your-api-key" \
  --name dm-service \
  ecommerce-dm-service
```

## Performance

Target response times:
- `/n8n/prepare-context`: < 150ms
- `/products/search`: < 100ms
- `/context/retrieve`: < 50ms
- `/cache/check`: < 30ms
- `/analytics/log`: < 50ms

## Multilingual Support

### Arabic Examples
- "كم سعر الجينز" → price_inquiry, product: jeans
- "عايز اشتري هودي اسود" → order_intent, product: hoodie, color: black
- "موجود مقاس 32؟" → availability_check, size: 32

### Franco-Arabic (Arabizi) Examples
- "3ayez jeans azra2" → order_intent, product: jeans, color: blue
- "b kam el shirt?" → price_inquiry, product: shirt
- "mawgood size L?" → availability_check, size: L

### English Examples
- "How much is the hoodie?" → price_inquiry, product: hoodie
- "I want to buy black jeans size 34" → order_intent, product: jeans, color: black, size: 34

## Architecture

```
main.py              # FastAPI app, routes, middleware
models.py            # Pydantic request/response models
database.py          # SQLAlchemy models, DB connection
config.py            # Environment configuration
auth.py              # API key auth, rate limiting
services/
  ├── products.py    # Multilingual product search
  ├── context.py     # Conversation management
  ├── intent.py      # Intent classification
  ├── cache.py       # Response caching
  └── analytics.py   # Analytics tracking
schema.sql           # Database migration
requirements.txt     # Python dependencies
Dockerfile           # Container image
.env.example         # Environment template
```

## Cost Savings

This microservice dramatically reduces OpenAI API costs:

1. **Smart Product Search** - Only sends 3-5 relevant products instead of 50+
2. **Response Caching** - Common questions (greetings, thanks) served from cache
3. **Intent-based Skipping** - Simple intents answered without AI
4. **Reduced Token Count** - Smaller, focused prompts

Expected savings: 60-80% reduction in AI API costs.

## Security

- API key authentication on all endpoints
- Rate limiting (100 requests/minute default)
- Input validation via Pydantic
- SQL injection prevention via SQLAlchemy ORM
- Non-root Docker user
- No secrets in code (environment variables)

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License
