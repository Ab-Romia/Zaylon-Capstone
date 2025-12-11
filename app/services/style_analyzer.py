"""
Customer Style Analyzer
Phase 4: Analyzes customer communication patterns for style matching.

Detects:
- Language preference
- Formality level (formal, neutral, casual)
- Emoji usage patterns
- Message length preference
- Tone and sentiment
"""
import re
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from app.search.multilingual import detect_language

logger = logging.getLogger(__name__)


@dataclass
class CustomerStyle:
    """Customer communication style profile."""

    # Language
    primary_language: str  # en, es, ar, fr, de, pt, ar-franco

    # Formality (0-100 scale)
    formality_score: int  # 0=very casual, 50=neutral, 100=very formal
    formality_level: str  # "casual", "neutral", "formal"

    # Emoji usage
    uses_emojis: bool
    emoji_frequency: float  # emojis per message
    emoji_style: str  # "none", "minimal", "moderate", "heavy"

    # Message style
    avg_message_length: int  # words per message
    message_style: str  # "brief", "normal", "detailed"

    # Punctuation patterns
    uses_punctuation: bool
    uses_capitalization: bool

    # Tone indicators
    tone: str  # "friendly", "business", "urgent", "neutral"

    # Additional patterns
    uses_greetings: bool
    uses_questions: bool

    # Confidence
    confidence: float  # 0.0-1.0, based on message count


class StyleAnalyzer:
    """
    Analyzes customer communication style from message history.

    Features:
    - Multi-language support
    - Pattern detection across messages
    - Style consistency tracking
    - Confidence scoring
    """

    # Formal indicators
    FORMAL_INDICATORS = [
        # English
        r'\b(sir|madam|maam|please|kindly|would you|could you|may i|thank you very much)\b',
        # Arabic
        r'\b(حضرتك|سيادتك|من فضلك|لو سمحت|شكرا جزيلا)\b',
        # Spanish
        r'\b(señor|señora|por favor|muchas gracias|disculpe)\b',
        # French
        r'\b(monsieur|madame|s\'il vous plaît|merci beaucoup)\b',
    ]

    # Casual indicators
    CASUAL_INDICATORS = [
        # English
        r'\b(hey|hi|hello|yo|sup|yeah|yep|nah|gonna|wanna|dunno|lol|haha|omg|btw)\b',
        # Arabic/Franco-Arabic
        r'\b(هاي|ايه|ازيك|عامل|ايه|كول|تمام|ماشي|3aml|ezayk|tmam|kol|7aga|haha)\b',
        # Spanish
        r'\b(hola|qué tal|vale|ok|jaja|guay)\b',
    ]

    # Greeting patterns
    GREETING_PATTERNS = [
        r'\b(hi|hello|hey|good morning|good evening|greetings)\b',
        r'\b(مرحبا|السلام عليكم|صباح الخير|مساء الخير|اهلا)\b',
        r'\b(hola|buenos días|buenas tardes)\b',
        r'\b(bonjour|bonsoir|salut)\b',
    ]

    # Urgent tone indicators
    URGENT_INDICATORS = [
        r'\b(urgent|asap|now|immediately|quickly|fast|hurry)\b',
        r'\b(عاجل|سريع|فوري|دلوقتي|الحين)\b',
        r'\b(urgente|rápido|ahora)\b',
        r'!!!',
        r'URGENT',
        r'PLEASE HELP',
    ]

    def __init__(self):
        """Initialize style analyzer with compiled patterns."""
        self.formal_pattern = re.compile(
            '|'.join(self.FORMAL_INDICATORS),
            re.IGNORECASE
        )
        self.casual_pattern = re.compile(
            '|'.join(self.CASUAL_INDICATORS),
            re.IGNORECASE
        )
        self.greeting_pattern = re.compile(
            '|'.join(self.GREETING_PATTERNS),
            re.IGNORECASE
        )
        self.urgent_pattern = re.compile(
            '|'.join(self.URGENT_INDICATORS),
            re.IGNORECASE
        )

        # Emoji pattern (Unicode ranges for common emojis)
        self.emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )

    def analyze_messages(self, messages: List[str]) -> CustomerStyle:
        """
        Analyze customer style from message history.

        Args:
            messages: List of customer messages (most recent first)

        Returns:
            CustomerStyle profile
        """
        if not messages:
            return self._default_style()

        # Analyze each message
        analyses = [self._analyze_single_message(msg) for msg in messages]

        # Aggregate results
        return self._aggregate_analyses(analyses, len(messages))

    def _analyze_single_message(self, message: str) -> Dict[str, Any]:
        """Analyze a single message for style indicators."""
        message_lower = message.lower()

        # Language detection
        language = detect_language(message)

        # Formality detection
        formal_matches = len(self.formal_pattern.findall(message_lower))
        casual_matches = len(self.casual_pattern.findall(message_lower))

        # Emoji detection
        emojis = self.emoji_pattern.findall(message)
        emoji_count = len(emojis)

        # Punctuation
        has_punctuation = bool(re.search(r'[.!?,;:]', message))
        has_capitalization = bool(re.search(r'[A-Z]', message))

        # Message length (words)
        words = message.split()
        word_count = len(words)

        # Greetings
        has_greeting = bool(self.greeting_pattern.search(message_lower))

        # Questions
        has_question = '?' in message

        # Urgent tone
        has_urgent = bool(self.urgent_pattern.search(message))

        return {
            "language": language,
            "formal_count": formal_matches,
            "casual_count": casual_matches,
            "emoji_count": emoji_count,
            "word_count": word_count,
            "has_punctuation": has_punctuation,
            "has_capitalization": has_capitalization,
            "has_greeting": has_greeting,
            "has_question": has_question,
            "has_urgent": has_urgent
        }

    def _aggregate_analyses(
        self,
        analyses: List[Dict[str, Any]],
        message_count: int
    ) -> CustomerStyle:
        """Aggregate multiple message analyses into a style profile."""

        # Language (most common)
        languages = [a["language"] for a in analyses]
        primary_language = max(set(languages), key=languages.count)

        # Formality calculation
        total_formal = sum(a["formal_count"] for a in analyses)
        total_casual = sum(a["casual_count"] for a in analyses)

        if total_formal + total_casual == 0:
            formality_score = 50  # Neutral
        else:
            # Scale: more formal indicators = higher score
            formality_score = int((total_formal / (total_formal + total_casual)) * 100)

        if formality_score >= 70:
            formality_level = "formal"
        elif formality_score >= 40:
            formality_level = "neutral"
        else:
            formality_level = "casual"

        # Emoji usage
        total_emojis = sum(a["emoji_count"] for a in analyses)
        emoji_frequency = total_emojis / message_count
        uses_emojis = emoji_frequency > 0

        if emoji_frequency == 0:
            emoji_style = "none"
        elif emoji_frequency < 0.5:
            emoji_style = "minimal"
        elif emoji_frequency < 2.0:
            emoji_style = "moderate"
        else:
            emoji_style = "heavy"

        # Message length
        avg_message_length = int(sum(a["word_count"] for a in analyses) / message_count)

        if avg_message_length < 5:
            message_style = "brief"
        elif avg_message_length < 15:
            message_style = "normal"
        else:
            message_style = "detailed"

        # Punctuation and capitalization
        uses_punctuation = sum(1 for a in analyses if a["has_punctuation"]) / message_count > 0.5
        uses_capitalization = sum(1 for a in analyses if a["has_capitalization"]) / message_count > 0.5

        # Tone detection
        uses_greetings = any(a["has_greeting"] for a in analyses)
        has_urgent = any(a["has_urgent"] for a in analyses)

        if has_urgent:
            tone = "urgent"
        elif formality_score >= 70:
            tone = "business"
        elif uses_greetings or formality_score < 40:
            tone = "friendly"
        else:
            tone = "neutral"

        # Questions
        uses_questions = any(a["has_question"] for a in analyses)

        # Confidence based on message count
        if message_count >= 10:
            confidence = 0.95
        elif message_count >= 5:
            confidence = 0.80
        elif message_count >= 3:
            confidence = 0.65
        else:
            confidence = 0.50

        return CustomerStyle(
            primary_language=primary_language,
            formality_score=formality_score,
            formality_level=formality_level,
            uses_emojis=uses_emojis,
            emoji_frequency=emoji_frequency,
            emoji_style=emoji_style,
            avg_message_length=avg_message_length,
            message_style=message_style,
            uses_punctuation=uses_punctuation,
            uses_capitalization=uses_capitalization,
            tone=tone,
            uses_greetings=uses_greetings,
            uses_questions=uses_questions,
            confidence=confidence
        )

    def _default_style(self) -> CustomerStyle:
        """Return default neutral style when no messages available."""
        return CustomerStyle(
            primary_language="en",
            formality_score=50,
            formality_level="neutral",
            uses_emojis=False,
            emoji_frequency=0.0,
            emoji_style="none",
            avg_message_length=10,
            message_style="normal",
            uses_punctuation=True,
            uses_capitalization=True,
            tone="neutral",
            uses_greetings=False,
            uses_questions=False,
            confidence=0.0
        )

    def generate_style_instructions(self, style: CustomerStyle) -> str:
        """
        Generate instructions for LLM to match customer's style.

        Args:
            style: Customer style profile

        Returns:
            String with style matching instructions
        """
        instructions = []

        # Language
        lang_names = {
            "en": "English",
            "es": "Spanish",
            "ar": "Arabic",
            "ar-franco": "Franco-Arabic (transliterated Arabic)",
            "fr": "French",
            "de": "German",
            "pt": "Portuguese"
        }
        language_name = lang_names.get(style.primary_language, "English")
        instructions.append(f"**Language**: Respond in {language_name}.")

        # Formality
        if style.formality_level == "formal":
            instructions.append(
                f"**Formality**: Customer is formal (score: {style.formality_score}/100). "
                "Use professional language, complete sentences, and polite expressions. "
                "Examples: 'Thank you for contacting us', 'I would be happy to assist you', 'May I help you with'"
            )
        elif style.formality_level == "casual":
            instructions.append(
                f"**Formality**: Customer is casual (score: {style.formality_score}/100). "
                "Use friendly, conversational language. "
                "Examples: 'Hey!', 'Sure thing!', 'No problem', 'Got it'"
            )
        else:
            instructions.append(
                f"**Formality**: Customer is neutral (score: {style.formality_score}/100). "
                "Use balanced, professional but friendly language."
            )

        # Emoji usage
        if style.emoji_style == "heavy":
            instructions.append(
                f"**Emojis**: Customer uses emojis frequently ({style.emoji_frequency:.1f} per message). "
                "Match their energy with 2-3 emojis per response. "
                "Examples: 😊 👍 🎉 ✨"
            )
        elif style.emoji_style == "moderate":
            instructions.append(
                f"**Emojis**: Customer uses some emojis ({style.emoji_frequency:.1f} per message). "
                "Use 1-2 emojis occasionally to match their style."
            )
        elif style.emoji_style == "minimal":
            instructions.append(
                "**Emojis**: Customer uses emojis sparingly. Use at most 1 emoji if appropriate."
            )
        else:
            instructions.append(
                "**Emojis**: Customer doesn't use emojis. Avoid using emojis in your response."
            )

        # Message length
        if style.message_style == "brief":
            instructions.append(
                f"**Message Length**: Customer prefers brief messages (~{style.avg_message_length} words). "
                "Keep responses concise and to the point. 1-2 sentences preferred."
            )
        elif style.message_style == "detailed":
            instructions.append(
                f"**Message Length**: Customer writes detailed messages (~{style.avg_message_length} words). "
                "Provide thorough, detailed responses with complete explanations."
            )
        else:
            instructions.append(
                f"**Message Length**: Customer writes normal-length messages (~{style.avg_message_length} words). "
                "Use balanced, clear responses."
            )

        # Tone
        if style.tone == "urgent":
            instructions.append(
                "**Tone**: Customer's message indicates urgency. "
                "Acknowledge the urgency, be prompt, and provide immediate actionable information."
            )
        elif style.tone == "friendly":
            instructions.append(
                "**Tone**: Customer is friendly and warm. "
                "Match their warmth with a welcoming, personable tone."
            )
        elif style.tone == "business":
            instructions.append(
                "**Tone**: Customer is business-like. "
                "Maintain a professional, efficient tone focused on solutions."
            )

        # Punctuation
        if not style.uses_punctuation:
            instructions.append(
                "**Punctuation**: Customer uses minimal punctuation. "
                "You should still use proper punctuation for clarity, but keep it simple."
            )

        return "\n".join(instructions)


# Singleton instance
_style_analyzer: Optional[StyleAnalyzer] = None


def get_style_analyzer() -> StyleAnalyzer:
    """Get or create the global style analyzer instance."""
    global _style_analyzer
    if _style_analyzer is None:
        _style_analyzer = StyleAnalyzer()
    return _style_analyzer
