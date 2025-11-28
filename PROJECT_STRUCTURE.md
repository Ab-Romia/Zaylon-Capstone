# AI Microservices - Project Structure

## Overview
This project has been reorganized into a clean, scalable, and maintainable structure following Python best practices.

## Directory Structure

```
AI_Microservices/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   │
│   ├── api/                      # API layer
│   │   ├── __init__.py
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── router.py         # Aggregated API router
│   │       └── endpoints/        # Route handlers
│   │           ├── __init__.py
│   │           ├── n8n.py        # n8n integration endpoints
│   │           ├── products.py   # Product search endpoints
│   │           ├── analytics.py  # Analytics endpoints
│   │           ├── context.py    # Conversation context endpoints
│   │           ├── cache.py      # Response cache endpoints
│   │           ├── rag.py        # RAG system endpoints
│   │           ├── intent.py     # Intent classification endpoints
│   │           └── health.py     # Health check endpoint
│   │
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py             # Configuration management
│   │   ├── security.py           # Authentication & authorization
│   │   ├── constants.py          # Application constants
│   │   ├── enums.py              # Enumerations
│   │   └── background.py         # Background task manager
│   │
│   ├── models/                   # Database models (SQLAlchemy ORM)
│   │   ├── __init__.py
│   │   ├── base.py               # Base model class
│   │   ├── product.py            # Product model
│   │   ├── order.py              # Order model
│   │   ├── conversation.py       # Conversation model
│   │   ├── customer.py           # Customer model
│   │   ├── cache.py              # Response cache model
│   │   └── analytics.py          # Analytics event model
│   │
│   ├── schemas/                  # Pydantic schemas (API contracts)
│   │   ├── __init__.py
│   │   ├── common.py             # Common schemas (errors, health)
│   │   ├── products.py           # Product-related schemas
│   │   ├── orders.py             # Order-related schemas
│   │   ├── context.py            # Conversation context schemas
│   │   ├── intent.py             # Intent classification schemas
│   │   ├── cache.py              # Cache-related schemas
│   │   ├── analytics.py          # Analytics schemas
│   │   ├── rag.py                # RAG system schemas
│   │   └── n8n.py                # n8n integration schemas
│   │
│   ├── services/                 # Business logic layer
│   │   ├── __init__.py
│   │   ├── products.py           # Product search service
│   │   ├── orders.py             # Order management service
│   │   ├── context.py            # Conversation context service
│   │   ├── intent.py             # Intent classification service
│   │   ├── cache.py              # Response caching service
│   │   ├── analytics.py          # Analytics service
│   │   ├── rag.py                # RAG service
│   │   ├── embeddings.py         # Embedding generation service
│   │   ├── vector_db.py          # Vector database service
│   │   └── ingestion.py          # Data ingestion service
│   │
│   ├── db/                       # Database layer
│   │   ├── __init__.py
│   │   └── session.py            # Database session management
│   │
│   └── utils/                    # Utility functions
│       └── __init__.py
│
├── scripts/                      # Standalone scripts
│   ├── add_sample_products.py    # Add sample products to database
│   ├── get_render_db_url.py      # Get database URL for Render deployment
│   ├── check_instagram_setup.sh  # Check Instagram integration setup
│   └── test_*.py                 # Various test scripts
│
├── tests/                        # Test files (future use)
│   ├── __init__.py
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
│
├── .env                          # Environment variables (not in git)
├── .env.example                  # Example environment variables
├── .gitignore                    # Git ignore file
├── docker-compose.yml            # Docker Compose configuration
├── Dockerfile                    # Docker image definition
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

## Key Improvements

### 1. Separation of Concerns
- **Models** (`app/models/`): SQLAlchemy database models
- **Schemas** (`app/schemas/`): Pydantic validation models for API contracts
- **Services** (`app/services/`): Business logic layer
- **API** (`app/api/`): Route handlers and API structure

### 2. Clean Architecture
- Database layer (`app/db/`)
- Core functionality (`app/core/`)
- Versioned API (`app/api/v1/`)
- Utility functions (`app/utils/`)

### 3. Scalability Features
- Modular structure allows easy addition of new features
- API versioning support (v1, v2, etc.)
- Clear dependency flow
- Easy to test individual components

### 4. Better Organization
- Related code grouped together
- Explicit imports
- Proper Python package structure
- Scripts separated from application code

## Running the Application

### Development
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker
```bash
docker-compose up
```

## API Structure

All API endpoints are now prefixed with `/api/v1/`:

- `/api/v1/health` - Health check
- `/api/v1/products/*` - Product endpoints
- `/api/v1/context/*` - Conversation context endpoints
- `/api/v1/intent/*` - Intent classification endpoints
- `/api/v1/cache/*` - Response cache endpoints
- `/api/v1/analytics/*` - Analytics endpoints
- `/api/v1/n8n/*` - n8n integration endpoints
- `/api/v1/rag/*` - RAG system endpoints

## Import Patterns

### Database Models
```python
from app.models import Product, Order, Customer
```

### Database Session
```python
from app.db import get_db, init_db
```

### API Schemas
```python
from app.schemas import ProductSearchRequest, ProductSearchResponse
```

### Core Functionality
```python
from app.core.config import get_settings
from app.core.security import verify_api_key
from app.core.constants import MAX_PRODUCT_SEARCH_RESULTS
```

### Services
```python
from app.services import products, context, analytics
```

## Migration from Old Structure

The old files have been kept for reference:
- `main.py` (old) → `app/main.py` (new)
- `database.py` (old) → `app/models/*` + `app/db/session.py` (new)
- `models.py` (old) → `app/schemas/*` (new)
- `config.py` (old) → `app/core/config.py` (new)
- `auth.py` (old) → `app/core/security.py` (new)

You can safely remove the old files after confirming everything works.

## Benefits

1. **Maintainability**: Clear structure makes it easy to find and modify code
2. **Scalability**: Easy to add new features without cluttering existing code
3. **Testability**: Modular structure allows for better unit testing
4. **Collaboration**: Team members can work on different modules without conflicts
5. **Professional**: Follows Python and FastAPI best practices
6. **Future-Ready**: Structure supports growth and new features

## Next Steps

1. Consider adding Alembic for database migrations
2. Implement comprehensive test suite in `tests/`
3. Add API documentation with more examples
4. Consider adding monitoring and observability
5. Implement CI/CD pipelines
