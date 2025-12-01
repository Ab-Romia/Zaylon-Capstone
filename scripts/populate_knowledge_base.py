"""
Script to populate the knowledge base with essential FAQs.
Run this after server startup to add missing FAQs identified in evaluation.
"""
import asyncio
import logging
from services.ingestion import get_ingestion_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Essential FAQs identified from evaluation failures
KNOWLEDGE_BASE_DOCS = [
    {
        "doc_id": "return_policy",
        "content": """Return Policy

We offer a 30-day return policy for all products. Here are the details:

**Return Window**: You can return any item within 30 days of delivery for a full refund or exchange.

**Condition**: Items must be in original condition with tags attached and unworn/unused.

**Process**:
1. Contact our customer service team with your order number
2. Package the item securely in its original packaging
3. We'll arrange pickup or provide return shipping instructions
4. Once received and inspected, refunds are processed within 5-7 business days

**Refunds**: Refunds are issued to the original payment method. Shipping costs are non-refundable unless the return is due to our error.

**Exchanges**: Free exchanges for different sizes or colors within 30 days.

For questions, contact support@zaylon.com or call +20 123 456 7890.""",
        "metadata": {
            "title": "Return Policy",
            "category": "policies",
            "tags": ["return", "refund", "exchange", "policy"]
        }
    },
    {
        "doc_id": "shipping_policy",
        "content": """Shipping Information

**Shipping Locations**:
We ship to all major cities in Egypt including:
- Cairo and Greater Cairo
- Alexandria
- Giza
- Luxor
- Aswan
- Hurghada
- Sharm El-Sheikh
- All other Egyptian governorates

**Shipping Times**:
- Cairo and Giza: 1-2 business days
- Alexandria: 2-3 business days
- Other major cities: 3-5 business days
- Remote areas: 5-7 business days

**Shipping Costs**:
- Orders over 500 EGP: FREE shipping
- Orders under 500 EGP: 30 EGP shipping fee
- Express delivery (next-day in Cairo): 50 EGP

**Tracking**: All orders include tracking. You'll receive a tracking number via SMS and email once your order ships.

**International Shipping**: Currently, we only ship within Egypt. International shipping coming soon!""",
        "metadata": {
            "title": "Shipping Policy",
            "category": "policies",
            "tags": ["shipping", "delivery", "cairo", "egypt", "locations"]
        }
    },
    {
        "doc_id": "payment_methods",
        "content": """Payment Methods

We accept the following payment methods:

**Credit/Debit Cards**:
- Visa
- Mastercard
- American Express
- Meeza (Egyptian local cards)

**Digital Wallets**:
- Vodafone Cash
- Orange Cash
- Etisalat Cash
- Fawry

**Cash on Delivery (COD)**:
- Available for all orders
- Pay in cash when you receive your order
- Small COD fee of 10 EGP applies

**Bank Transfer**:
- Available for orders over 1000 EGP
- Contact support for bank details
- Order ships after payment confirmation

**Security**: All online payments are processed through secure, encrypted payment gateways. We never store your card information.

**Currency**: All prices are in Egyptian Pounds (EGP).""",
        "metadata": {
            "title": "Payment Methods",
            "category": "policies",
            "tags": ["payment", "credit card", "cash", "vodafone", "fawry"]
        }
    },
    {
        "doc_id": "order_cancellation",
        "content": """How to Cancel Your Order

You can cancel your order if it hasn't shipped yet.

**Before Shipment**:
1. Contact customer support immediately at support@zaylon.com or +20 123 456 7890
2. Provide your order number
3. We'll cancel and refund your order within 24 hours

**After Shipment**:
- Once shipped, orders cannot be cancelled
- You can refuse delivery or initiate a return once received
- See our Return Policy for details

**Refund Timeline**:
- Credit/Debit cards: 5-7 business days
- Digital wallets: 1-3 business days
- Cash on Delivery: No refund needed if cancelled before shipment

**Automatic Cancellations**:
- Orders not confirmed within 48 hours are auto-cancelled
- Out-of-stock items may result in partial cancellations

For urgent cancellations, call us at +20 123 456 7890 (9 AM - 6 PM daily).""",
        "metadata": {
            "title": "Order Cancellation",
            "category": "policies",
            "tags": ["cancel", "cancellation", "order", "refund"]
        }
    },
    {
        "doc_id": "order_modification",
        "content": """Changing Your Order

**Before Shipment**:
You can modify your order (size, color, quantity) before it ships:
1. Contact customer support at support@zaylon.com or +20 123 456 7890
2. Provide your order number and the changes you want
3. We'll update your order if the items are available
4. You'll receive a confirmation of the changes

**What You Can Change**:
- Product size
- Product color
- Quantity (add or remove items)
- Delivery address
- Delivery time preference

**What You Cannot Change**:
- Payment method (must cancel and reorder)
- Apply discount codes after order placement

**After Shipment**:
- Orders cannot be modified once shipped
- You can initiate a return/exchange upon delivery
- See our Exchange Policy for details

**Response Time**: We process modification requests within 2-4 hours during business hours (9 AM - 6 PM).""",
        "metadata": {
            "title": "Order Modification",
            "category": "policies",
            "tags": ["change order", "modify", "update order", "size change"]
        }
    },
    {
        "doc_id": "damaged_items",
        "content": """Damaged or Defective Items Policy

We're sorry if you received a damaged item. Here's what to do:

**Immediate Steps**:
1. Take photos of the damaged item and packaging
2. Do NOT discard the item or packaging
3. Contact us within 48 hours of delivery at support@zaylon.com or +20 123 456 7890

**Resolution Options**:
1. **Full Refund**: Return the item for a complete refund
2. **Replacement**: We'll send you a new item at no cost
3. **Partial Refund**: Keep the item with a discount (for minor defects)

**Return Process for Damaged Items**:
- FREE return pickup at your location
- No questions asked, full refund or replacement
- Refund processed within 3-5 business days

**Quality Guarantee**:
All our products undergo quality checks. If you receive a damaged item, it's our error and we'll make it right immediately.

**Manufacturing Defects**:
- Covered for 90 days from purchase
- Free replacement or full refund
- Includes issues like stitching defects, color fading, fabric tears

**Contact**: support@zaylon.com | +20 123 456 7890 (9 AM - 6 PM daily)""",
        "metadata": {
            "title": "Damaged Items Policy",
            "category": "policies",
            "tags": ["damaged", "defective", "broken", "complaint", "quality"]
        }
    },
    {
        "doc_id": "sizing_guide",
        "content": """Sizing Guide

**Size Chart** (measurements in cm):

T-Shirts and Tops:
- XS: Chest 86-89, Length 66
- S: Chest 91-94, Length 69
- M: Chest 96-99, Length 72
- L: Chest 102-105, Length 74
- XL: Chest 107-112, Length 76
- XXL: Chest 114-119, Length 78

Hoodies and Sweatshirts:
- XS: Chest 91-94, Length 63
- S: Chest 96-99, Length 66
- M: Chest 102-105, Length 69
- L: Chest 107-112, Length 72
- XL: Chest 114-119, Length 74

Pants and Jeans:
- 28: Waist 71, Hips 86-89
- 30: Waist 76, Hips 91-94
- 32: Waist 81, Hips 96-99
- 34: Waist 86, Hips 102-105
- 36: Waist 91, Hips 107-112
- 38: Waist 96, Hips 114-119

**How to Measure**:
- Chest: Measure around the fullest part
- Length: From shoulder to hem
- Waist: Measure around natural waistline

**Fit Tips**:
- If between sizes, size up for relaxed fit
- Size down for fitted look
- Check product descriptions for fit notes

**Still Unsure?**: Contact us at support@zaylon.com with your measurements for personalized recommendations.""",
        "metadata": {
            "title": "Sizing Guide",
            "category": "guides",
            "tags": ["size", "sizing", "measurements", "fit"]
        }
    }
]


async def populate_knowledge_base():
    """Populate the knowledge base with essential FAQs."""
    logger.info("Starting knowledge base population...")

    ingestion_service = get_ingestion_service()

    success_count = 0
    fail_count = 0

    for doc in KNOWLEDGE_BASE_DOCS:
        try:
            logger.info(f"Indexing document: {doc['doc_id']}")
            success = await ingestion_service.index_knowledge_document(
                doc_id=doc['doc_id'],
                content=doc['content'],
                metadata=doc.get('metadata', {})
            )

            if success:
                success_count += 1
                logger.info(f"✓ Successfully indexed: {doc['doc_id']}")
            else:
                fail_count += 1
                logger.error(f"✗ Failed to index: {doc['doc_id']}")
        except Exception as e:
            fail_count += 1
            logger.error(f"✗ Error indexing {doc['doc_id']}: {e}")

    logger.info(f"\n{'='*60}")
    logger.info(f"Knowledge Base Population Complete")
    logger.info(f"{'='*60}")
    logger.info(f"✓ Successfully indexed: {success_count}")
    logger.info(f"✗ Failed: {fail_count}")
    logger.info(f"{'='*60}\n")

    return success_count, fail_count


if __name__ == "__main__":
    asyncio.run(populate_knowledge_base())
