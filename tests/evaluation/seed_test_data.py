"""
Seed test data for evaluation suite.
Creates orders and customer facts for test users.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from database import async_session, Order, CustomerFact
from sqlalchemy import delete


async def seed_test_data():
    """Seed test data for evaluation customers."""
    print("\n[INFO] Seeding test data for evaluation suite...")

    async with async_session() as db:
        # Clean up existing test data
        print("[INFO] Cleaning up existing test data...")
        await db.execute(delete(Order).where(Order.customer_id.like("eval_test_%")))
        await db.execute(delete(CustomerFact).where(CustomerFact.customer_id.like("eval_test_%")))
        await db.commit()

        # Test 4: "Where is my order?" - needs order
        print("[INFO] Creating order for Test 4 (order tracking)...")
        order_4 = Order(
            customer_id="eval_test_4",
            product_id="test_product_1",
            product_name="Black Hoodie Premium",
            size="L",
            color="black",
            quantity=1,
            total_price=450.0,
            customer_name="Test User 4",
            phone="+201234567890",
            address="123 Test Street, Cairo",
            channel="instagram",
            status="shipped",
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        db.add(order_4)

        # Test 5: "Return last order + buy blue shirt" - needs order history
        print("[INFO] Creating order for Test 5 (return + purchase)...")
        order_5 = Order(
            customer_id="eval_test_5",
            product_id="test_product_2",
            product_name="Urban Street Hoodie",
            size="M",
            color="Gray",
            quantity=1,
            total_price=65.5,
            customer_name="Test User 5",
            phone="+201234567891",
            address="456 Test Avenue, Cairo",
            channel="instagram",
            status="delivered",
            created_at=datetime.utcnow() - timedelta(days=5)
        )
        db.add(order_5)

        # Test 6: "That hoodie in my size" - needs customer size preference
        print("[INFO] Creating customer facts for Test 6 (memory retrieval)...")
        fact_6_size = CustomerFact(
            customer_id="eval_test_6",
            fact_type="preference",
            fact_key="preferred_size",
            fact_value="L",
            confidence=100,
            source="explicit"
        )
        fact_6_product = CustomerFact(
            customer_id="eval_test_6",
            fact_type="preference",
            fact_key="last_viewed_product",
            fact_value="Essential Oversized Hoodie",
            confidence=90,
            source="inferred"
        )
        db.add(fact_6_size)
        db.add(fact_6_product)

        # Test 10: "Help with recent purchase" - needs order
        print("[INFO] Creating order for Test 10 (recent purchase support)...")
        order_10 = Order(
            customer_id="eval_test_10",
            product_id="test_product_3",
            product_name="Classic Blue Denim Jeans",
            size="32",
            color="blue",
            quantity=1,
            total_price=599.0,
            customer_name="Test User 10",
            phone="+201234567892",
            address="789 Test Road, Cairo",
            channel="instagram",
            status="delivered",
            created_at=datetime.utcnow() - timedelta(days=1)
        )
        db.add(order_10)

        # Test 11: "Can I change my order?" - needs pending order
        print("[INFO] Creating order for Test 11 (order modification)...")
        order_11 = Order(
            customer_id="eval_test_11",
            product_id="test_product_4",
            product_name="Cargo Techwear Pants",
            size="32",
            color="black",
            quantity=1,
            total_price=95.0,
            customer_name="Test User 11",
            phone="+201234567893",
            address="321 Test Lane, Cairo",
            channel="instagram",
            status="pending",
            created_at=datetime.utcnow() - timedelta(hours=2)
        )
        db.add(order_11)

        # Test 19: "Show products in my favorite color" - needs color preference
        print("[INFO] Creating customer facts for Test 19 (favorite color)...")
        fact_19_color = CustomerFact(
            customer_id="eval_test_19",
            fact_type="preference",
            fact_key="favorite_color",
            fact_value="blue",
            confidence=100,
            source="explicit"
        )
        fact_19_size = CustomerFact(
            customer_id="eval_test_19",
            fact_type="preference",
            fact_key="preferred_size",
            fact_value="M",
            confidence=100,
            source="explicit"
        )
        db.add(fact_19_color)
        db.add(fact_19_size)

        # Test 20: "Order #12345 status" - create specific order
        print("[INFO] Creating order #12345 for Test 20...")
        order_20 = Order(
            id="12345",
            customer_id="eval_test_20",
            product_id="test_product_5",
            product_name="Essential Oversized Hoodie",
            size="XL",
            color="Black",
            quantity=2,
            total_price=130.0,
            customer_name="Test User 20",
            phone="+201234567894",
            address="555 Test Blvd, Cairo",
            channel="instagram",
            status="processing",
            created_at=datetime.utcnow() - timedelta(hours=6)
        )
        db.add(order_20)

        # Test 21: Arabic "فين طلبي?" - needs order
        print("[INFO] Creating order for Test 21 (Arabic order tracking)...")
        order_21 = Order(
            customer_id="eval_test_21",
            product_id="test_product_6",
            product_name="Cargo Techwear Pants",
            size="34",
            color="olive",
            quantity=1,
            total_price=95.0,
            customer_name="Test User 21",
            phone="+201234567895",
            address="777 Test Street, Alexandria",
            channel="instagram",
            status="shipped",
            created_at=datetime.utcnow() - timedelta(days=3)
        )
        db.add(order_21)

        # Test 26: "Ordered shirt but want pants" - needs shirt order
        print("[INFO] Creating order for Test 26 (order change)...")
        order_26 = Order(
            customer_id="eval_test_26",
            product_id="test_product_7",
            product_name="Classic Cotton T-Shirt",
            size="L",
            color="white",
            quantity=1,
            total_price=199.0,
            customer_name="Test User 26",
            phone="+201234567896",
            address="888 Test Avenue, Giza",
            channel="instagram",
            status="pending",
            created_at=datetime.utcnow() - timedelta(hours=4)
        )
        db.add(order_26)

        # Test 30: "Reorder last purchase" - needs order history
        print("[INFO] Creating order for Test 30 (reorder)...")
        order_30 = Order(
            customer_id="eval_test_30",
            product_id="ad3eaf17-bd25-4a1d-9d40-50b24ed20361",  # Real product ID from DB
            product_name="Street Runner Sneakers",
            size="US 10",
            color="White/Blue",
            quantity=1,
            total_price=110.0,
            customer_name="Test User 30",
            phone="+201234567897",
            address="999 Test Road, Cairo",
            channel="instagram",
            status="delivered",
            created_at=datetime.utcnow() - timedelta(days=10)
        )
        db.add(order_30)

        await db.commit()
        print("\n[OK] Test data seeded successfully!")
        print(f"  - Created 10 test orders")
        print(f"  - Created 5 customer facts")
        print(f"  - Ready for evaluation suite")


if __name__ == "__main__":
    print("\n" + "="*80)
    print("TEST DATA SEEDING FOR EVALUATION SUITE")
    print("="*80)

    try:
        asyncio.run(seed_test_data())
    except KeyboardInterrupt:
        print("\n\n[CANCELLED] Seeding cancelled by user")
    except Exception as e:
        print(f"\n\n[ERROR] Seeding failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
