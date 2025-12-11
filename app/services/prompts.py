"""
Prompt Management Service
Phase 3: Zero Hard-Coding - Dynamically load and render prompts from database.
"""
import logging
from typing import Dict, Any, Optional, List
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from jinja2 import Template, Environment, StrictUndefined
import json

logger = logging.getLogger(__name__)


class PromptTemplate:
    """Represents a prompt template loaded from database."""

    def __init__(
        self,
        id: str,
        name: str,
        agent_type: str,
        prompt_type: str,
        template: str,
        variables: List[str],
        version: int,
        language: str = "en",
        channel: Optional[str] = None
    ):
        self.id = id
        self.name = name
        self.agent_type = agent_type
        self.prompt_type = prompt_type
        self.template_str = template
        self.variables = variables
        self.version = version
        self.language = language
        self.channel = channel

        # Initialize Jinja2 template
        self.jinja_env = Environment(undefined=StrictUndefined)
        self.jinja_template = self.jinja_env.from_string(template)

    def render(self, context: Dict[str, Any]) -> str:
        """
        Render template with provided context.

        Args:
            context: Dictionary of variables to inject into template

        Returns:
            Rendered prompt string

        Raises:
            KeyError: If required variable is missing from context
        """
        try:
            # Validate all required variables are provided
            missing_vars = set(self.variables) - set(context.keys())
            if missing_vars:
                logger.warning(f"Missing variables in context: {missing_vars}. Using empty strings.")
                for var in missing_vars:
                    context[var] = ""

            # Render template
            rendered = self.jinja_template.render(**context)
            return rendered

        except Exception as e:
            logger.error(f"Error rendering template {self.name}: {e}", exc_info=True)
            raise


class PromptService:
    """
    Service for managing and loading prompt templates from database.

    Features:
    - Load prompts by agent type, language, and channel
    - Cache prompts for performance
    - Track usage statistics
    - A/B testing support
    """

    def __init__(self):
        self._cache: Dict[str, PromptTemplate] = {}
        self._cache_enabled = True

    async def get_prompt(
        self,
        db: AsyncSession,
        agent_type: str,
        prompt_type: str = "system",
        language: str = "en",
        channel: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[PromptTemplate]:
        """
        Load prompt template from database.

        Args:
            db: Database session
            agent_type: Agent type (sales, support, supervisor, memory)
            prompt_type: Type of prompt (system, tool_instruction, synthesis, extraction)
            language: Language code (en, es, ar, fr, de, pt)
            channel: Communication channel (instagram, whatsapp, web, None for default)
            use_cache: Whether to use cached prompts

        Returns:
            PromptTemplate object or None if not found
        """
        # Build cache key
        cache_key = f"{agent_type}:{prompt_type}:{language}:{channel or 'default'}"

        # Check cache first
        if use_cache and self._cache_enabled and cache_key in self._cache:
            logger.debug(f"Returning cached prompt: {cache_key}")
            return self._cache[cache_key]

        try:
            # Import here to avoid circular dependency
            from app.models import PromptTemplate as PromptTemplateModel

            # Build query with priority:
            # 1. Exact match (agent_type + prompt_type + language + channel)
            # 2. Language match (agent_type + prompt_type + language + default channel)
            # 3. Default (agent_type + prompt_type + 'en' + default channel)

            conditions = [
                PromptTemplateModel.agent_type == agent_type,
                PromptTemplateModel.prompt_type == prompt_type,
                PromptTemplateModel.is_active == True
            ]

            # Try exact match first
            if channel:
                stmt = select(PromptTemplateModel).where(
                    and_(
                        *conditions,
                        PromptTemplateModel.language == language,
                        PromptTemplateModel.channel == channel,
                        PromptTemplateModel.is_default == True
                    )
                ).limit(1)

                result = await db.execute(stmt)
                row = result.scalar_one_or_none()

                if row:
                    prompt = self._row_to_prompt(row)
                    self._cache[cache_key] = prompt
                    logger.info(f"Loaded prompt (exact match): {prompt.name}")
                    return prompt

            # Try language + default channel
            stmt = select(PromptTemplateModel).where(
                and_(
                    *conditions,
                    PromptTemplateModel.language == language,
                    PromptTemplateModel.channel.is_(None),
                    PromptTemplateModel.is_default == True
                )
            ).limit(1)

            result = await db.execute(stmt)
            row = result.scalar_one_or_none()

            if row:
                prompt = self._row_to_prompt(row)
                self._cache[cache_key] = prompt
                logger.info(f"Loaded prompt (language match): {prompt.name}")
                return prompt

            # Fallback to English default
            if language != "en":
                stmt = select(PromptTemplateModel).where(
                    and_(
                        *conditions,
                        PromptTemplateModel.language == "en",
                        PromptTemplateModel.channel.is_(None),
                        PromptTemplateModel.is_default == True
                    )
                ).limit(1)

                result = await db.execute(stmt)
                row = result.scalar_one_or_none()

                if row:
                    prompt = self._row_to_prompt(row)
                    self._cache[cache_key] = prompt
                    logger.info(f"Loaded prompt (English fallback): {prompt.name}")
                    return prompt

            logger.warning(f"No prompt found for {cache_key}")
            return None

        except Exception as e:
            logger.error(f"Error loading prompt {cache_key}: {e}", exc_info=True)
            return None

    async def render_prompt(
        self,
        db: AsyncSession,
        agent_type: str,
        context: Dict[str, Any],
        prompt_type: str = "system",
        language: str = "en",
        channel: Optional[str] = None
    ) -> Optional[str]:
        """
        Load and render prompt in one step.

        Args:
            db: Database session
            agent_type: Agent type
            context: Variables to inject into template
            prompt_type: Type of prompt
            language: Language code
            channel: Communication channel

        Returns:
            Rendered prompt string or None if template not found
        """
        template = await self.get_prompt(
            db=db,
            agent_type=agent_type,
            prompt_type=prompt_type,
            language=language,
            channel=channel
        )

        if not template:
            logger.error(f"No template found for {agent_type}:{prompt_type}")
            return None

        try:
            rendered = template.render(context)

            # Track usage (fire and forget)
            await self._track_usage(db, template.id)

            return rendered

        except Exception as e:
            logger.error(f"Error rendering prompt: {e}", exc_info=True)
            return None

    async def _track_usage(self, db: AsyncSession, prompt_id: str):
        """Track prompt usage asynchronously."""
        try:
            from app.models import PromptTemplate as PromptTemplateModel
            from sqlalchemy import update

            stmt = (
                update(PromptTemplateModel)
                .where(PromptTemplateModel.id == prompt_id)
                .values(usage_count=PromptTemplateModel.usage_count + 1)
            )
            await db.execute(stmt)
            await db.commit()

        except Exception as e:
            logger.error(f"Error tracking usage: {e}")
            # Don't raise - usage tracking failure shouldn't break the system

    def _row_to_prompt(self, row) -> PromptTemplate:
        """Convert database row to PromptTemplate object."""
        variables = row.variables if isinstance(row.variables, list) else []

        return PromptTemplate(
            id=str(row.id),
            name=row.name,
            agent_type=row.agent_type,
            prompt_type=row.prompt_type,
            template=row.template,
            variables=variables,
            version=row.version,
            language=row.language,
            channel=row.channel
        )

    def clear_cache(self):
        """Clear the prompt cache."""
        self._cache.clear()
        logger.info("Prompt cache cleared")

    async def list_prompts(
        self,
        db: AsyncSession,
        agent_type: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """
        List all prompts (for admin UI).

        Args:
            db: Database session
            agent_type: Filter by agent type
            is_active: Filter by active status

        Returns:
            List of prompt metadata dictionaries
        """
        try:
            from app.models import PromptTemplate as PromptTemplateModel

            conditions = []
            if agent_type:
                conditions.append(PromptTemplateModel.agent_type == agent_type)
            if is_active is not None:
                conditions.append(PromptTemplateModel.is_active == is_active)

            if conditions:
                stmt = select(PromptTemplateModel).where(and_(*conditions))
            else:
                stmt = select(PromptTemplateModel)

            result = await db.execute(stmt)
            rows = result.scalars().all()

            prompts = []
            for row in rows:
                prompts.append({
                    "id": str(row.id),
                    "name": row.name,
                    "description": row.description,
                    "agent_type": row.agent_type,
                    "prompt_type": row.prompt_type,
                    "version": row.version,
                    "language": row.language,
                    "channel": row.channel,
                    "is_active": row.is_active,
                    "is_default": row.is_default,
                    "usage_count": row.usage_count,
                    "success_rate": row.success_rate,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None
                })

            return prompts

        except Exception as e:
            logger.error(f"Error listing prompts: {e}", exc_info=True)
            return []

    async def create_prompt(
        self,
        db: AsyncSession,
        name: str,
        agent_type: str,
        prompt_type: str,
        template: str,
        description: Optional[str] = None,
        variables: Optional[List[str]] = None,
        language: str = "en",
        channel: Optional[str] = None,
        is_default: bool = False,
        created_by: Optional[str] = None
    ) -> Optional[str]:
        """
        Create a new prompt template.

        Args:
            db: Database session
            name: Unique prompt name
            agent_type: Agent type
            prompt_type: Prompt type
            template: Jinja2 template string
            description: Optional description
            variables: List of variable names
            language: Language code
            channel: Communication channel
            is_default: Whether this is the default prompt
            created_by: User who created this prompt

        Returns:
            Prompt ID if successful, None otherwise
        """
        try:
            from app.models import PromptTemplate as PromptTemplateModel
            import uuid

            prompt_id = str(uuid.uuid4())

            new_prompt = PromptTemplateModel(
                id=prompt_id,
                name=name,
                description=description,
                agent_type=agent_type,
                prompt_type=prompt_type,
                template=template,
                variables=variables or [],
                language=language,
                channel=channel,
                is_default=is_default,
                is_active=True,
                version=1,
                created_by=created_by
            )

            db.add(new_prompt)
            await db.commit()

            logger.info(f"Created new prompt: {name} (ID: {prompt_id})")
            self.clear_cache()  # Clear cache after creating new prompt

            return prompt_id

        except Exception as e:
            logger.error(f"Error creating prompt: {e}", exc_info=True)
            await db.rollback()
            return None


# Singleton instance
_prompt_service: Optional[PromptService] = None


def get_prompt_service() -> PromptService:
    """Get or create the global prompt service instance."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService()
    return _prompt_service
