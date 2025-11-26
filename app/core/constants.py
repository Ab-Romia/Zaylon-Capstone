"""Constants used throughout the application."""

# Message processing
MESSAGE_TRUNCATE_LENGTH = 500
CONTEXT_HISTORY_DISPLAY_LIMIT = 10

# Caching
CONTEXT_CACHE_TTL = 30  # seconds
MAX_CACHE_SIZE = 1000
CACHE_EVICTION_BATCH = 100

# AI Cost estimation (OpenAI GPT-4 pricing)
AI_COST_PER_1K_INPUT = 0.03   # $0.03 per 1K input tokens
AI_COST_PER_1K_OUTPUT = 0.06  # $0.06 per 1K output tokens
AI_INPUT_TOKEN_RATIO = 0.6    # Assume 60% input
AI_OUTPUT_TOKEN_RATIO = 0.4   # Assume 40% output

# Regex patterns
PHONE_PATTERN = r'(?:\+?20|0)?1[0125]\d{8}'
NAME_PATTERNS = [
    r'(?:my name is|اسمي|ana|i\'m|i am)\s+([a-zA-Z\u0600-\u06FF]+)',
    r'(?:name:|الاسم:?)\s+([a-zA-Z\u0600-\u06FF]+)',
]

# Embedding dimensions
EMBEDDING_DIMENSION_OPENAI = 1536
EMBEDDING_DIMENSION_LOCAL = 384

# Rate limiting
DEFAULT_RATE_LIMIT = 100  # per minute
BULK_INDEX_RATE_LIMIT = "5/hour"

# Database
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 10
DB_POOL_RECYCLE = 3600
DB_CONNECT_TIMEOUT = 30
DB_COMMAND_TIMEOUT = 60

# Order history
DEFAULT_ORDER_HISTORY_LIMIT = 5

# Search
DEFAULT_SEARCH_LIMIT = 5
MAX_SEARCH_LIMIT = 20

# Background task queue size
BACKGROUND_QUEUE_SIZE = 1000
