"""
Script to index ALL knowledge base documents from Supabase into Qdrant.
This pulls from the knowledge_base table and indexes each document.
Run this after updating knowledge base content in Supabase.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add parent directory to path to import from app
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from database import async_session, KnowledgeBase
from services.ingestion import get_ingestion_service
from services.vector_db import get_vector_db
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def index_all_knowledge_from_db():
    """
    Index all active knowledge base documents from the database.
    """
    settings = get_settings()
    ingestion_service = get_ingestion_service()
    vector_db = get_vector_db()

    logger.info("="*70)
    logger.info("INDEXING KNOWLEDGE BASE FROM DATABASE")
    logger.info("="*70)

    # Check Qdrant connection
    if not vector_db.is_connected():
        logger.error("❌ Qdrant is not connected. Check QDRANT_URL and QDRANT_API_KEY")
        return False

    logger.info("✅ Qdrant connected")

    # Get all active knowledge base documents
    async with async_session() as session:
        try:
            stmt = select(KnowledgeBase).where(KnowledgeBase.is_active == True)
            result = await session.execute(stmt)
            kb_docs = result.scalars().all()

            total = len(kb_docs)
            logger.info(f"📚 Found {total} active knowledge base documents in database")

            if total == 0:
                logger.warning("⚠️  No active knowledge base documents found!")
                return False

            # Index each document
            indexed = 0
            failed = 0

            for i, doc in enumerate(kb_docs, 1):
                logger.info(f"\n[{i}/{total}] Indexing: {doc.doc_id} - {doc.title or 'No title'}")

                # Build metadata
                metadata = {}
                if doc.title:
                    metadata["title"] = doc.title
                if doc.category:
                    metadata["category"] = doc.category
                if doc.tags:
                    metadata["tags"] = doc.tags
                if doc.metadata:
                    # Merge existing metadata (JSONB field - might be dict or string)
                    try:
                        if isinstance(doc.metadata, dict):
                            metadata.update(doc.metadata)
                        elif isinstance(doc.metadata, str):
                            import json
                            metadata.update(json.loads(doc.metadata))
                    except Exception as e:
                        logger.warning(f"  ⚠️  Could not parse metadata: {e}")

                # Index the document
                try:
                    success = await ingestion_service.index_knowledge_document(
                        doc_id=doc.doc_id,
                        content=doc.content,
                        metadata=metadata
                    )

                    if success:
                        indexed += 1
                        logger.info(f"  ✅ Successfully indexed")
                    else:
                        failed += 1
                        logger.error(f"  ❌ Failed to index")

                except Exception as e:
                    failed += 1
                    logger.error(f"  ❌ Error indexing: {e}")

            # Summary
            logger.info("\n" + "="*70)
            logger.info("INDEXING COMPLETE")
            logger.info("="*70)
            logger.info(f"Total documents: {total}")
            logger.info(f"Successfully indexed: {indexed}")
            logger.info(f"Failed: {failed}")

            # Verify collection
            kb_info = await vector_db.get_collection_info(settings.qdrant_collection_knowledge)
            if kb_info:
                logger.info(f"\n📊 Knowledge Base Collection Status:")
                logger.info(f"   Points count: {kb_info.get('points_count', 'unknown')}")
                logger.info(f"   Vectors dimension: {kb_info.get('vector_size', 'unknown')}")

            return indexed > 0

        except Exception as e:
            logger.error(f"❌ Database error: {e}")
            return False


if __name__ == "__main__":
    result = asyncio.run(index_all_knowledge_from_db())
    sys.exit(0 if result else 1)
