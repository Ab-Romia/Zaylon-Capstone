"""
Multilingual support for search queries.
Handles language detection, query enhancement, and synonym expansion.
"""
import re
import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# Language detection patterns
LANGUAGE_PATTERNS = {
    "arabic": re.compile(r'[\u0600-\u06FF]+'),  # Arabic Unicode range
    "spanish": {
        "keywords": ["que", "como", "donde", "cuando", "por", "para", "con", "sin"],
        "chars": ["á", "é", "í", "ó", "ú", "ñ", "ü"]
    },
    "french": {
        "keywords": ["que", "qui", "où", "quand", "pour", "avec", "sans", "dans"],
        "chars": ["à", "è", "é", "ê", "ë", "î", "ï", "ô", "ù", "û", "ü", "ç", "œ"]
    },
    "german": {
        "keywords": ["und", "oder", "nicht", "mit", "ohne", "für", "von", "zu"],
        "chars": ["ä", "ö", "ü", "ß"]
    },
    "portuguese": {
        "keywords": ["que", "como", "onde", "quando", "por", "para", "com", "sem"],
        "chars": ["ã", "õ", "á", "é", "í", "ó", "ú", "â", "ê", "ô", "ç"]
    },
    "franco_arabic": re.compile(r'\b[a-z]*[0-9][a-z0-9]*\b', re.IGNORECASE)  # Contains numbers
}

# Product synonyms by language
PRODUCT_SYNONYMS = {
    # English
    "en": {
        "shirt": ["t-shirt", "tee", "top", "blouse", "polo"],
        "pants": ["trousers", "jeans", "slacks", "bottoms"],
        "hoodie": ["sweatshirt", "pullover", "sweater"],
        "jacket": ["coat", "blazer", "outerwear"],
        "shoes": ["footwear", "sneakers", "boots"],
        "dress": ["gown", "frock", "outfit"]
    },
    # Spanish
    "es": {
        "camiseta": ["camisa", "playera", "polo", "top", "shirt", "t-shirt"],
        "pantalón": ["pantalones", "jeans", "vaqueros", "pants", "trousers"],
        "sudadera": ["hoodie", "suéter", "sweater", "sweatshirt"],
        "chaqueta": ["abrigo", "chamarra", "saco", "jacket", "coat"],
        "zapatos": ["calzado", "zapatillas", "botas", "shoes", "sneakers"],
        "vestido": ["dress", "traje"]
    },
    # Arabic
    "ar": {
        "قميص": ["تيشيرت", "تي شيرت", "بولو", "shirt", "t-shirt"],
        "بنطلون": ["بنطال", "جينز", "جينس", "pants", "jeans"],
        "هودي": ["سويتر", "بلوفر", "hoodie", "sweater"],
        "جاكيت": ["جاكت", "معطف", "jacket", "coat"],
        "حذاء": ["احذية", "كوتشي", "بوت", "shoes", "sneakers"],
        "فستان": ["dress", "جلباب"]
    },
    # French
    "fr": {
        "chemise": ["t-shirt", "polo", "haut", "shirt"],
        "pantalon": ["jeans", "pantalons", "pants", "trousers"],
        "sweat": ["sweat-shirt", "pull", "hoodie", "sweater"],
        "veste": ["manteau", "blouson", "jacket", "coat"],
        "chaussures": ["baskets", "bottes", "shoes", "sneakers"],
        "robe": ["dress"]
    },
    # German
    "de": {
        "hemd": ["t-shirt", "shirt", "polo"],
        "hose": ["jeans", "hosen", "pants", "trousers"],
        "hoodie": ["pullover", "sweatshirt", "sweater"],
        "jacke": ["mantel", "jacket", "coat"],
        "schuhe": ["sneakers", "stiefel", "shoes", "boots"],
        "kleid": ["dress"]
    },
    # Portuguese
    "pt": {
        "camisa": ["camiseta", "polo", "blusa", "shirt", "t-shirt"],
        "calça": ["calças", "jeans", "pants", "trousers"],
        "moletom": ["hoodie", "suéter", "sweater"],
        "jaqueta": ["casaco", "jacket", "coat"],
        "sapatos": ["tênis", "botas", "shoes", "sneakers"],
        "vestido": ["dress"]
    }
}

# Color synonyms by language
COLOR_SYNONYMS = {
    "en": {
        "black": ["negro", "noir", "schwarz", "preto", "اسود", "أسود"],
        "white": ["blanco", "blanc", "weiß", "branco", "ابيض", "أبيض"],
        "red": ["rojo", "rouge", "rot", "vermelho", "احمر", "أحمر"],
        "blue": ["azul", "bleu", "blau", "ازرق", "أزرق"],
        "green": ["verde", "vert", "grün", "اخضر", "أخضر"],
        "yellow": ["amarillo", "jaune", "gelb", "amarelo", "اصفر", "أصفر"],
        "gray": ["gris", "grau", "cinza", "رمادي", "رصاصي"],
        "pink": ["rosa", "rose", "rosa", "وردي", "زهري"],
        "brown": ["marrón", "marron", "braun", "marrom", "بني"],
        "navy": ["azul marino", "bleu marine", "marineblau", "كحلي", "كحل"]
    }
}


def detect_language(query: str) -> str:
    """
    Detect the language of a search query.

    Args:
        query: Search query string

    Returns:
        Language code: "en", "es", "ar", "fr", "de", "pt", "ar-franco", or "unknown"
    """
    query_lower = query.lower()

    # Check for Arabic script
    if LANGUAGE_PATTERNS["arabic"].search(query):
        return "ar"

    # Check for Franco-Arabic (numbers mixed with Latin letters)
    if LANGUAGE_PATTERNS["franco_arabic"].search(query):
        # Additional check: if it has typical franco-arabic patterns
        if any(num in query_lower for num in ["3", "7", "2", "5", "8", "9"]):
            return "ar-franco"

    # Check for Spanish
    spanish_score = 0
    if any(char in query_lower for char in LANGUAGE_PATTERNS["spanish"]["chars"]):
        spanish_score += 2
    if any(word in query_lower.split() for word in LANGUAGE_PATTERNS["spanish"]["keywords"]):
        spanish_score += 1
    if spanish_score >= 2:
        return "es"

    # Check for French
    french_score = 0
    if any(char in query_lower for char in LANGUAGE_PATTERNS["french"]["chars"]):
        french_score += 2
    if any(word in query_lower.split() for word in LANGUAGE_PATTERNS["french"]["keywords"]):
        french_score += 1
    if french_score >= 2:
        return "fr"

    # Check for German
    german_score = 0
    if any(char in query_lower for char in LANGUAGE_PATTERNS["german"]["chars"]):
        german_score += 2
    if any(word in query_lower.split() for word in LANGUAGE_PATTERNS["german"]["keywords"]):
        german_score += 1
    if german_score >= 2:
        return "de"

    # Check for Portuguese
    portuguese_score = 0
    if any(char in query_lower for char in LANGUAGE_PATTERNS["portuguese"]["chars"]):
        portuguese_score += 2
    if any(word in query_lower.split() for word in LANGUAGE_PATTERNS["portuguese"]["keywords"]):
        portuguese_score += 1
    if portuguese_score >= 2:
        return "pt"

    # Default to English
    return "en"


def get_language_specific_synonyms(word: str, language: str) -> List[str]:
    """
    Get synonyms for a word in a specific language.

    Args:
        word: Word to find synonyms for
        language: Language code

    Returns:
        List of synonyms including the original word
    """
    word_lower = word.lower()
    synonyms = [word]  # Always include original

    # Get synonyms from the language-specific dictionary
    if language in PRODUCT_SYNONYMS:
        for key, syn_list in PRODUCT_SYNONYMS[language].items():
            if word_lower == key or word_lower in syn_list:
                synonyms.extend([key] + syn_list)
                break

    # Also check English synonyms (cross-lingual)
    if language != "en" and "en" in PRODUCT_SYNONYMS:
        for key, syn_list in PRODUCT_SYNONYMS["en"].items():
            if word_lower in syn_list:
                synonyms.extend([key] + syn_list)
                break

    # Remove duplicates while preserving order
    seen = set()
    unique_synonyms = []
    for syn in synonyms:
        syn_lower = syn.lower()
        if syn_lower not in seen:
            seen.add(syn_lower)
            unique_synonyms.append(syn)

    return unique_synonyms


def enhance_query(query: str, language: Optional[str] = None) -> str:
    """
    Enhance search query with synonyms and language-specific expansions.

    Args:
        query: Original search query
        language: Language code (auto-detected if not provided)

    Returns:
        Enhanced query string with synonyms
    """
    if language is None:
        language = detect_language(query)

    words = query.split()
    enhanced_words = []

    for word in words:
        # Get synonyms for this word
        synonyms = get_language_specific_synonyms(word, language)

        # If we found synonyms, add them
        if len(synonyms) > 1:
            # Add original word and top 2-3 synonyms
            enhanced_words.append(word)
            enhanced_words.extend(synonyms[1:4])  # Add up to 3 synonyms
        else:
            enhanced_words.append(word)

    # Remove duplicates while preserving order
    seen = set()
    result = []
    for word in enhanced_words:
        word_lower = word.lower()
        if word_lower not in seen:
            seen.add(word_lower)
            result.append(word)

    enhanced = " ".join(result)
    logger.info(f"Enhanced query: '{query}' → '{enhanced}' (language: {language})")
    return enhanced


def translate_query(query: str, target_language: str = "en") -> str:
    """
    Translate query to target language using synonym mapping.

    Args:
        query: Original query
        target_language: Target language code

    Returns:
        Translated query (best effort using synonyms)
    """
    source_language = detect_language(query)

    if source_language == target_language:
        return query

    # Simple translation using synonym mappings
    words = query.split()
    translated_words = []

    for word in words:
        word_lower = word.lower()
        translated = word

        # Try to find translation
        if source_language in PRODUCT_SYNONYMS:
            for key, syn_list in PRODUCT_SYNONYMS[source_language].items():
                if word_lower == key:
                    # Found the word, now find English equivalent
                    if target_language == "en":
                        # Look for English synonym
                        for syn in syn_list:
                            if syn in ["shirt", "t-shirt", "pants", "trousers", "hoodie", "sweater", "jacket", "coat", "shoes", "sneakers", "dress"]:
                                translated = syn
                                break
                    break

        translated_words.append(translated)

    result = " ".join(translated_words)
    logger.info(f"Translated query: '{query}' ({source_language}) → '{result}' ({target_language})")
    return result


def extract_product_types_multilingual(query: str) -> List[Tuple[str, str]]:
    """
    Extract product types from query with their detected language.

    Args:
        query: Search query

    Returns:
        List of (product_type, language) tuples
    """
    language = detect_language(query)
    products = []

    # Check all product types in the detected language
    if language in PRODUCT_SYNONYMS:
        for key, synonyms in PRODUCT_SYNONYMS[language].items():
            # Check if key or any synonym appears in query
            query_lower = query.lower()
            if key in query_lower:
                products.append((key, language))
            else:
                for syn in synonyms:
                    if syn.lower() in query_lower:
                        products.append((key, language))
                        break

    return products


def extract_colors_multilingual(query: str) -> List[str]:
    """
    Extract color names from query in any language.

    Args:
        query: Search query

    Returns:
        List of color names (normalized to English)
    """
    query_lower = query.lower()
    colors = []

    # Check all color synonyms
    for color_en, synonyms in COLOR_SYNONYMS["en"].items():
        # Check English color name
        if color_en in query_lower:
            colors.append(color_en)
        # Check synonyms in other languages
        else:
            for syn in synonyms:
                if syn in query_lower:
                    colors.append(color_en)
                    break

    return list(set(colors))  # Remove duplicates
