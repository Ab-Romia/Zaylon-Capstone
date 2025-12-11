"""
Validation script to verify all Qdrant collections have data.
Run this after ingestion scripts to ensure deployment is healthy.
"""
import sys
import logging
import warnings
from services.vector_db import get_vector_db
from config import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def validate_qdrant_collections():
    """
    Verify all Qdrant collections have data.
    Exits with code 1 if any collection is empty or inaccessible.
    """
    logger.info("="*60)
    logger.info("QDRANT COLLECTIONS VALIDATION")
    logger.info("="*60)

    # Load settings
    try:
        settings = get_settings()
        logger.info(f"Settings loaded successfully")
        logger.info(f"  Qdrant URL: {settings.qdrant_url}")
    except Exception as e:
        logger.error(f"❌ Failed to load settings: {e}")
        sys.exit(1)

    # Connect to Qdrant
    try:
        vector_db = get_vector_db()
        if not vector_db.is_connected():
            logger.error(f"❌ Qdrant is not connected")
            logger.error(f"   Check QDRANT_URL and QDRANT_API_KEY environment variables")
            sys.exit(1)
        logger.info(f"✅ Qdrant connection successful\n")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Qdrant: {e}")
        sys.exit(1)

    # Collections to check
    collections_to_check = [
        {
            "name": settings.qdrant_collection_products,
            "min_expected": 1,
            "description": "Products"
        },
        {
            "name": settings.qdrant_collection_knowledge,
            "min_expected": 1,
            "description": "Knowledge Base"
        }
    ]

    all_valid = True
    validation_results = []

    # Validate each collection
    for collection in collections_to_check:
        collection_name = collection["name"]
        min_expected = collection["min_expected"]
        description = collection["description"]

        try:
            # Get collection info
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore")
                collection_info = vector_db.client.get_collection(collection_name)
                points_count = collection_info.points_count

            if points_count == 0:
                logger.error(f"❌ Collection '{collection_name}' ({description}): EMPTY (0 points)")
                all_valid = False
                validation_results.append({
                    "collection": collection_name,
                    "status": "FAIL",
                    "points": 0,
                    "reason": "Collection is empty"
                })
            elif points_count < min_expected:
                logger.warning(f"⚠️  Collection '{collection_name}' ({description}): {points_count} points (expected >= {min_expected})")
                validation_results.append({
                    "collection": collection_name,
                    "status": "WARNING",
                    "points": points_count,
                    "reason": f"Less than expected minimum ({min_expected})"
                })
            else:
                logger.info(f"✅ Collection '{collection_name}' ({description}): {points_count} points")
                validation_results.append({
                    "collection": collection_name,
                    "status": "OK",
                    "points": points_count
                })
        except Exception as e:
            logger.error(f"❌ Error checking collection '{collection_name}': {e}")
            all_valid = False
            validation_results.append({
                "collection": collection_name,
                "status": "ERROR",
                "reason": str(e)
            })

    # Print summary
    logger.info("\n" + "="*60)
    logger.info("VALIDATION SUMMARY")
    logger.info("="*60)
    for result in validation_results:
        status_icon = "✅" if result["status"] == "OK" else "⚠️" if result["status"] == "WARNING" else "❌"
        if "points" in result:
            logger.info(f"{status_icon} {result['collection']}: {result['points']} points ({result['status']})")
        else:
            logger.info(f"{status_icon} {result['collection']}: {result['status']} - {result['reason']}")
    logger.info("="*60)

    if all_valid:
        logger.info("\n✅ ALL COLLECTIONS VALIDATED SUCCESSFULLY")
        logger.info("="*60 + "\n")
        sys.exit(0)
    else:
        logger.error("\n❌ VALIDATION FAILED - Fix issues above before deploying")
        logger.info("="*60 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    try:
        validate_qdrant_collections()
    except KeyboardInterrupt:
        logger.warning("\n⚠️  Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"\n❌ FATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
