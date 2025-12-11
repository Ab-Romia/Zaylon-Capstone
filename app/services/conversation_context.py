"""
Conversation Context Service
Phase 4: Extracts conversation history and applies style matching.

Integrates:
- Message history extraction
- Customer style analysis
- Style-aware prompt enhancement
"""
import logging
from typing import List, Dict, Any, Optional
from langchain_core.messages import HumanMessage, AIMessage, BaseMessage

from app.services.style_analyzer import get_style_analyzer, CustomerStyle

logger = logging.getLogger(__name__)


class ConversationContextService:
    """
    Service for managing conversation context and style matching.

    Features:
    - Extract customer messages from conversation
    - Analyze customer communication style
    - Generate style-aware prompt instructions
    - Track conversation patterns
    """

    def __init__(self):
        self.style_analyzer = get_style_analyzer()

    def extract_customer_messages(
        self,
        messages: List[BaseMessage],
        limit: int = 10
    ) -> List[str]:
        """
        Extract customer (human) messages from conversation history.

        Args:
            messages: List of conversation messages
            limit: Maximum number of messages to extract (most recent)

        Returns:
            List of customer message texts (most recent first)
        """
        customer_messages = []

        # Iterate in reverse to get most recent first
        for message in reversed(messages):
            if isinstance(message, HumanMessage):
                if message.content and message.content.strip():
                    customer_messages.append(message.content.strip())

                if len(customer_messages) >= limit:
                    break

        return customer_messages

    def analyze_customer_style(
        self,
        messages: List[BaseMessage]
    ) -> CustomerStyle:
        """
        Analyze customer communication style from conversation history.

        Args:
            messages: List of conversation messages

        Returns:
            CustomerStyle profile
        """
        # Extract customer messages
        customer_messages = self.extract_customer_messages(messages, limit=10)

        if not customer_messages:
            logger.warning("No customer messages found for style analysis")
            return self.style_analyzer._default_style()

        # Analyze style
        style = self.style_analyzer.analyze_messages(customer_messages)

        logger.info(
            f"Customer style analyzed: language={style.primary_language}, "
            f"formality={style.formality_level} ({style.formality_score}), "
            f"emojis={style.emoji_style}, "
            f"tone={style.tone}, "
            f"confidence={style.confidence:.2f}"
        )

        return style

    def get_style_instructions(
        self,
        messages: List[BaseMessage]
    ) -> str:
        """
        Get style matching instructions for LLM prompt.

        Args:
            messages: List of conversation messages

        Returns:
            Formatted string with style instructions
        """
        style = self.analyze_customer_style(messages)
        instructions = self.style_analyzer.generate_style_instructions(style)
        return instructions

    def enhance_prompt_with_style(
        self,
        base_prompt: str,
        messages: List[BaseMessage],
        insert_marker: str = "**COMMUNICATION STYLE**:"
    ) -> str:
        """
        Enhance a prompt with style matching instructions.

        Args:
            base_prompt: Base agent prompt
            messages: Conversation messages
            insert_marker: Where to insert style instructions (default: after customer context)

        Returns:
            Enhanced prompt with style instructions
        """
        style_instructions = self.get_style_instructions(messages)

        # Insert style instructions after the marker
        if insert_marker in base_prompt:
            parts = base_prompt.split(insert_marker, 1)
            enhanced_prompt = (
                parts[0] +
                insert_marker +
                "\n" +
                style_instructions +
                "\n\n" +
                parts[1]
            )
        else:
            # If marker not found, append at end before tool lists
            if "**Available Tools**:" in base_prompt:
                parts = base_prompt.split("**Available Tools**:", 1)
                enhanced_prompt = (
                    parts[0] +
                    "\n**COMMUNICATION STYLE**:\n" +
                    style_instructions +
                    "\n\n**Available Tools**:" +
                    parts[1]
                )
            else:
                # Fallback: append at very end
                enhanced_prompt = (
                    base_prompt +
                    "\n\n**COMMUNICATION STYLE**:\n" +
                    style_instructions
                )

        return enhanced_prompt

    def get_conversation_summary(
        self,
        messages: List[BaseMessage],
        max_turns: int = 5
    ) -> Dict[str, Any]:
        """
        Get a summary of the conversation for context.

        Args:
            messages: List of conversation messages
            max_turns: Maximum number of turns to include

        Returns:
            Dictionary with conversation summary
        """
        customer_messages = self.extract_customer_messages(messages, limit=max_turns)
        style = self.analyze_customer_style(messages)

        # Count message types
        total_messages = len(messages)
        customer_count = sum(1 for m in messages if isinstance(m, HumanMessage))
        ai_count = sum(1 for m in messages if isinstance(m, AIMessage))

        return {
            "total_messages": total_messages,
            "customer_messages": customer_count,
            "ai_messages": ai_count,
            "recent_customer_messages": customer_messages[:3],  # Last 3
            "style_profile": {
                "language": style.primary_language,
                "formality": style.formality_level,
                "emoji_style": style.emoji_style,
                "tone": style.tone,
                "confidence": style.confidence
            }
        }


# Singleton instance
_conversation_context_service: Optional[ConversationContextService] = None


def get_conversation_context_service() -> ConversationContextService:
    """Get or create the global conversation context service."""
    global _conversation_context_service
    if _conversation_context_service is None:
        _conversation_context_service = ConversationContextService()
    return _conversation_context_service
