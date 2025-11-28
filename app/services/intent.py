"""
Hybrid intent classification service.
Uses rule-based patterns for speed, with entity extraction.
"""
import re
from typing import List, Optional, Tuple, Dict
from app.schemas import IntentClassifyResponse, ExtractedEntities
import logging

logger = logging.getLogger(__name__)

# Intent patterns - multilingual (Arabic, Franco-Arabic, English)
INTENT_PATTERNS = {
    "greeting": {
        "keywords": [
            "hi", "hello", "hey", "good morning", "good evening",
            "مرحبا", "السلام", "ازيك", "ازيكم", "صباح الخير", "مساء الخير",
            "اهلا", "هاي", "هلو", "ازاي", "عامل ايه",
            "salam", "ahlan", "marhaba", "ezayak", "ezayek"
        ],
        "priority": 1,
        "skip_ai": True,
        "suggested_response": "مرحبا! 👋 أنا هنا لمساعدتك. ازاي أقدر أساعدك النهارده؟ / Hello! I'm here to help. How can I assist you today?"
    },
    "thanks": {
        "keywords": [
            "thanks", "thank you", "thx", "ty", "appreciate",
            "شكرا", "متشكر", "شكر", "تسلم", "الله يعطيك العافية",
            "merci", "shokran"
        ],
        "priority": 1,
        "skip_ai": True,
        "suggested_response": "العفو! سعداء بخدمتك 😊 / You're welcome! Happy to help!"
    },
    "goodbye": {
        "keywords": [
            "bye", "goodbye", "see you", "later",
            "مع السلامة", "باي", "يلا باي", "الى اللقاء"
        ],
        "priority": 1,
        "skip_ai": True,
        "suggested_response": "مع السلامة! نتطلع لخدمتك مرة أخرى 👋 / Goodbye! Looking forward to serving you again!"
    },
    "price_inquiry": {
        "keywords": [
            "price", "cost", "how much", "pricing", "expensive", "cheap",
            "كم", "سعر", "بكم", "كام", "غالي", "رخيص", "تمن",
            "b kam", "kam", "se3r", "b3d kam"
        ],
        "priority": 2,
        "skip_ai": False,
        "suggested_response": None
    },
    "order_intent": {
        "keywords": [
            "buy", "order", "purchase", "want", "need", "get",
            "عايز", "عاوز", "اشتري", "طلب", "محتاج", "ابغى", "اريد",
            "3ayez", "3awez", "ashtry", "talab", "m7tag"
        ],
        "priority": 3,
        "skip_ai": False,
        "suggested_response": None
    },
    "availability_check": {
        "keywords": [
            "available", "stock", "in stock", "have", "got",
            "موجود", "متوفر", "عندكم", "فيه", "متاح",
            "mawgood", "متوفر", "3andoko"
        ],
        "priority": 2,
        "skip_ai": False,
        "suggested_response": None
    },
    "variant_inquiry": {
        "keywords": [
            "size", "sizes", "color", "colors", "colour",
            "مقاس", "مقاسات", "لون", "الوان", "سايز",
            "2as", "lon", "size", "saiz"
        ],
        "priority": 2,
        "skip_ai": False,
        "suggested_response": None
    },
    "order_status": {
        "keywords": [
            "order status", "where", "tracking", "delivery", "shipped", "arrived",
            "الطلب فين", "وين الطلب", "وصل", "شحن", "التوصيل",
            "talab fein", "wein", "shipping"
        ],
        "priority": 2,
        "skip_ai": False,
        "suggested_response": None
    },
    "complaint": {
        "keywords": [
            "problem", "issue", "wrong", "bad", "disappointed", "refund",
            "مشكلة", "غلط", "سيء", "زعلان", "استرجاع", "استبدال",
            "moshkela", "3'alt", "refund"
        ],
        "priority": 2,
        "skip_ai": False,
        "suggested_response": None
    }
}

# Entity extraction patterns
PHONE_PATTERNS = [
    r'(?:\+?20|0)?1[0125]\d{8}',  # Egyptian phone numbers
    r'\+?\d{10,15}'  # General international format
]

SIZE_PATTERNS = [
    (r'\b(xs|XS)\b', "XS"),
    (r'\b(s|S|small|صغير)\b', "S"),
    (r'\b(m|M|medium|وسط)\b', "M"),
    (r'\b(l|L|large|كبير)\b', "L"),
    (r'\b(xl|XL)\b', "XL"),
    (r'\b(xxl|XXL|2xl)\b', "XXL"),
    (r'\b(xxxl|XXXL|3xl)\b', "XXXL"),
    (r'\bsize\s*(\d{2})\b', None),  # Numeric size
    (r'\b(\d{2})\b', None),  # Standalone number (could be size)
]

COLOR_PATTERNS = {
    "black": [r'\b(black|اسود|أسود|eswed|aswad)\b'],
    "white": [r'\b(white|ابيض|أبيض|abyad|abyed)\b'],
    "red": [r'\b(red|احمر|أحمر|a7mar|ahmar)\b'],
    "blue": [r'\b(blue|ازرق|أزرق|azra2|azraq)\b'],
    "green": [r'\b(green|اخضر|أخضر|akhdar|a5dar)\b'],
    "yellow": [r'\b(yellow|اصفر|أصفر|asfar)\b'],
    "brown": [r'\b(brown|بني|bonny|bunni)\b'],
    "gray": [r'\b(gray|grey|رمادي|رصاصي|rasasi)\b'],
    "pink": [r'\b(pink|وردي|زهري|wardy)\b'],
    "orange": [r'\b(orange|برتقالي|borto2aly)\b'],
    "navy": [r'\b(navy|كحلي|كحل|ka7ly)\b'],
    "beige": [r'\b(beige|بيج|بيچ)\b'],
}

QUANTITY_PATTERNS = [
    r'(\d+)\s*(?:pieces?|pcs?|قطعة|قطع)',
    r'(\d+)\s*(?:items?|حتة|حبة)',
    r'quantity[:\s]+(\d+)',
    r'عدد[:\s]+(\d+)',
    r'^(\d+)$',  # Standalone number in context
]

PRODUCT_NAME_PATTERNS = {
    "jeans": [r'\b(jeans|جينز|جينس|jeanz|denim)\b'],
    "pants": [r'\b(pants|بنطلون|pantalon|trousers)\b'],
    "hoodie": [r'\b(hoodie|هودي|هوديز|hoody|sweatshirt)\b'],
    "shirt": [r'\b(shirt|شيرت|قميص|t-shirt|tshirt|tee)\b'],
    "jacket": [r'\b(jacket|جاكيت|جاكت|coat)\b'],
    "shoes": [r'\b(shoes|حذاء|جزمة|7ezaa2|gizma|sneakers)\b'],
    "dress": [r'\b(dress|فستان|fostan)\b'],
    "shorts": [r'\b(shorts|شورت|short)\b'],
    "bag": [r'\b(bag|شنطة|حقيبة|shanta)\b'],
}


def classify_intent(
    message: str,
    context: Optional[List[str]] = None
) -> IntentClassifyResponse:
    """
    Classify the intent of a message using rule-based patterns.

    Returns:
        IntentClassifyResponse with intent, confidence, entities, and suggested response
    """
    logger.info(f"Classifying intent for: {message[:100]}...")

    message_lower = message.lower()

    # Try to match intents
    matched_intent = None
    matched_priority = 999
    confidence = 0.0
    skip_ai = False
    suggested_response = None

    for intent_name, intent_data in INTENT_PATTERNS.items():
        keywords = intent_data["keywords"]
        priority = intent_data["priority"]

        for keyword in keywords:
            if keyword.lower() in message_lower:
                # Higher match = lower priority number = more specific
                if priority < matched_priority:
                    matched_intent = intent_name
                    matched_priority = priority
                    skip_ai = intent_data.get("skip_ai", False)
                    suggested_response = intent_data.get("suggested_response")
                    confidence = 0.85 if priority == 1 else 0.75
                break

    # Default to general_inquiry if no match
    if not matched_intent:
        matched_intent = "general_inquiry"
        confidence = 0.5
        skip_ai = False

    # Extract entities
    entities = extract_entities(message)

    # Boost confidence if we found relevant entities
    if entities.product_name and matched_intent in ["order_intent", "price_inquiry", "availability_check"]:
        confidence = min(confidence + 0.1, 0.95)

    # Adjust skip_ai based on entities
    # If we have specific product/order info, let AI handle it
    if entities.product_name or entities.size or entities.color:
        if matched_intent in ["greeting", "thanks", "goodbye"]:
            # Customer is greeting but also mentioning products
            matched_intent = "general_inquiry"
            skip_ai = False
            suggested_response = None
            confidence = 0.7

    logger.info(f"Classified as: {matched_intent} (confidence: {confidence:.2f})")

    return IntentClassifyResponse(
        intent=matched_intent,
        confidence=confidence,
        entities=entities,
        skip_ai=skip_ai,
        suggested_response=suggested_response
    )


def extract_entities(message: str) -> ExtractedEntities:
    """Extract entities (product, size, color, quantity, phone) from message."""
    product_name = None
    size = None
    color = None
    quantity = None
    phone = None

    # Extract phone
    for pattern in PHONE_PATTERNS:
        match = re.search(pattern, message)
        if match:
            phone = match.group(0)
            # Normalize Egyptian phone
            if phone.startswith("01"):
                phone = "+20" + phone[1:]
            elif phone.startswith("1") and len(phone) == 10:
                phone = "+20" + phone
            break

    # Extract size
    for pattern, fixed_size in SIZE_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            if fixed_size:
                size = fixed_size
            else:
                size = match.group(1).upper()
            break

    # Extract color
    for color_name, patterns in COLOR_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                color = color_name
                break
        if color:
            break

    # Extract product name
    for product, patterns in PRODUCT_NAME_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message, re.IGNORECASE):
                product_name = product
                break
        if product_name:
            break

    # Extract quantity
    for pattern in QUANTITY_PATTERNS:
        match = re.search(pattern, message, re.IGNORECASE)
        if match:
            try:
                qty = int(match.group(1))
                if 1 <= qty <= 100:  # Reasonable quantity range
                    quantity = qty
                    break
            except ValueError:
                pass

    return ExtractedEntities(
        product_name=product_name,
        size=size,
        color=color,
        quantity=quantity,
        phone=phone
    )


def get_skip_ai_response(intent: str) -> Optional[str]:
    """Get pre-defined response for skip_ai intents."""
    if intent in INTENT_PATTERNS:
        return INTENT_PATTERNS[intent].get("suggested_response")
    return None
