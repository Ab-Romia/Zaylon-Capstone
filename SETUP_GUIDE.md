# ZAYLON Complete Setup Guide

**Production-Ready Multi-Agent E-Commerce System**

This guide will get you from zero to demo-ready in under 30 minutes.

---

## Prerequisites

- Python 3.10+
- Node.js 18+
- PostgreSQL (or Supabase account)
- Qdrant (local or cloud)
- OpenAI API key or Google Gemini API key

---

## Part 1: Backend Setup (15 minutes)

### 1.1 Clone and Setup Environment

```bash
cd /home/user/AI_Microservices

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 1.2 Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env  # or use your preferred editor
```

**Required Environment Variables:**

```bash
# Database
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/zaylon

# API Security
API_KEY=your-secret-api-key-change-this

# LLM Provider (choose one)
LLM_PROVIDER=openai  # or "gemini"

# OpenAI (if using OpenAI)
OPENAI_API_KEY=sk-your-openai-api-key

# Gemini (if using Gemini)
GEMINI_API_KEY=your-gemini-api-key

# Vector Database
QDRANT_URL=http://localhost:6333
QDRANT_API_KEY=  # Optional for local Qdrant
```

### 1.3 Initialize Database

```bash
# Run Qdrant (if using Docker)
docker run -p 6333:6333 qdrant/qdrant

# Initialize database and populate sample data
python scripts/add_sample_products.py
python scripts/populate_knowledge_base.py
```

### 1.4 Start Backend Server

```bash
# Run with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# Server will be available at:
# http://localhost:8000
# API docs: http://localhost:8000/docs
```

### 1.5 Test Backend

```bash
# Health check
curl http://localhost:8000/api/v1/health

# Test agent invoke
curl -X POST "http://localhost:8000/api/v2/agent/invoke" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{
    "customer_id": "test:user123",
    "message": "Show me black hoodies",
    "channel": "instagram"
  }'

# Should return JSON with agent response
```

---

## Part 2: Web Interface Setup (10 minutes)

### 2.1 Navigate and Install

```bash
cd zaylon-web

# Install dependencies
npm install
```

### 2.2 Configure Environment

```bash
# Edit .env.local
nano .env.local

# Add your configuration:
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your-secret-api-key
```

### 2.3 Start Development Server

```bash
npm run dev

# Web interface will be available at:
# http://localhost:3000
```

### 2.4 Test Web Interface

1. Open http://localhost:3000 in your browser
2. Type a message: "I want a black hoodie in size M"
3. Watch the magic happen:
   - Process visualization shows each step
   - System logs display in real-time
   - Analytics update with metrics
   - Agent responds with streaming

---

## Part 3: Integration Tests (5 minutes)

### 3.1 Test Streaming Endpoint

```bash
# Test SSE streaming
curl -X POST "http://localhost:8000/api/v2/agent/stream" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-api-key" \
  -d '{
    "customer_id": "test:user456",
    "message": "What is your return policy?",
    "channel": "instagram"
  }'

# Should stream data: chunks in real-time
```

### 3.2 Verify All Components

**Backend Checklist:**
- [ ] Backend running on port 8000
- [ ] Database connected
- [ ] Qdrant connected
- [ ] Sample products loaded
- [ ] Knowledge base populated
- [ ] `/health` endpoint returns 200
- [ ] `/invoke` endpoint works
- [ ] `/stream` endpoint streams data

**Frontend Checklist:**
- [ ] Web interface running on port 3000
- [ ] Chat interface renders
- [ ] Messages send successfully
- [ ] Process visualization updates
- [ ] Analytics display metrics
- [ ] System logs show events
- [ ] Streaming works smoothly

---

## Part 4: Demo Preparation

### 4.1 Test Scenarios

Run through these scenarios to ensure everything works:

1. **Product Search**
   - "Show me hoodies"
   - "I want a black jacket"
   - "Do you have blue shirts?"

2. **Size Conversion**
   - "I need shoes in EU size 47"
   - "What's size 12 in UK?"

3. **Order Placement**
   - "I want to buy the black hoodie"
   - Agent should ask for: size, color, name, phone, address
   - Confirm order
   - Should return order ID

4. **Policy Questions**
   - "What's your return policy?"
   - "How long does shipping take?"
   - "Do you ship to Cairo?"

5. **Mixed Queries**
   - "I want a hoodie but first tell me about returns"
   - Agent should handle both parts

### 4.2 Performance Check

- Response time should be <5s for most queries
- Streaming should be smooth
- No errors in system logs
- All panels update in real-time

### 4.3 Polish

1. **Clear Test Data**
   ```bash
   # Clear conversation history if needed
   # Reset demo user state
   ```

2. **Prepare Demo Script**
   - Have 3-4 key scenarios ready
   - Know where to point attention (process viz, logs, analytics)
   - Highlight unique features:
     - Multi-agent routing
     - Tool usage transparency
     - Memory persistence
     - Size conversion
     - Streaming responses

3. **Screenshot/Record**
   - Take screenshots of key features
   - Record a demo video if needed

---

## Troubleshooting

### Backend Issues

**Port Already in Use:**
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn main:app --port 8001
```

**Database Connection Error:**
```bash
# Check DATABASE_URL format
# For local PostgreSQL:
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/zaylon

# For Supabase:
DATABASE_URL=postgresql+psycopg://[user]:[password]@[host]:5432/[database]
```

**Qdrant Not Connected:**
```bash
# Start Qdrant with Docker
docker run -p 6333:6333 qdrant/qdrant

# Check connection
curl http://localhost:6333/health
```

### Frontend Issues

**API Connection Failed:**
- Check `.env.local` has correct `NEXT_PUBLIC_API_URL`
- Ensure backend is running
- Verify API key matches

**Streaming Not Working:**
- Check browser console for errors
- Inspect Network tab for SSE connection
- Ensure CORS is enabled in backend

**Components Not Rendering:**
```bash
# Clear Next.js cache
rm -rf .next
npm run dev
```

---

## Production Deployment

### Backend (Render.com)

1. Push to GitHub
2. Connect Render to your repo
3. Configure environment variables
4. Deploy

See `render.yaml` for configuration.

### Frontend (Vercel)

```bash
cd zaylon-web
vercel

# Follow prompts
# Add environment variables in Vercel dashboard
```

---

## Maintenance

### Updating Sample Data

```bash
python scripts/add_sample_products.py  # Add more products
python scripts/populate_knowledge_base.py  # Update FAQs
```

### Monitoring

- Check `/api/v1/health` endpoint regularly
- Monitor system logs panel in web interface
- Review analytics for performance trends

### Scaling

- Use Qdrant Cloud for vector DB
- Deploy backend with multiple instances
- Use caching for frequent queries
- Enable CDN for web interface

---

## Success Criteria

You're ready for demo when:

- [ ] Backend responds in <5s
- [ ] All test scenarios work
- [ ] Web interface shows all panels correctly
- [ ] Streaming is smooth
- [ ] No errors in logs
- [ ] Process visualization displays correctly
- [ ] Analytics show accurate metrics
- [ ] Size conversion works
- [ ] Order creation returns order ID

---

## Getting Help

1. Check `ZAYLON_IMPLEMENTATION_STATUS.md` for detailed docs
2. Review component README in `zaylon-web/README.md`
3. Inspect browser console and backend logs
4. Test endpoints with curl/Postman

---

**Created by:** Abdelrahman Abouroumia (Romia) & Abdelrahman Mashaal
**Version:** 1.0.0
**Status:** Production Ready
**Last Updated:** 2025-12-01

---

## Quick Reference

**Start Everything:**
```bash
# Terminal 1: Backend
source venv/bin/activate
uvicorn main:app --reload

# Terminal 2: Frontend
cd zaylon-web
npm run dev

# Terminal 3: Qdrant (if using Docker)
docker run -p 6333:6333 qdrant/qdrant
```

**URLs:**
- Backend: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Web Interface: http://localhost:3000
- Qdrant: http://localhost:6333/dashboard

**Demo Message:**
"I want a black hoodie in size M. My name is Ahmed, phone is +201234567890, address is Cairo, Egypt."
