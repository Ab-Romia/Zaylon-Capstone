"""
Sample Product Data Loader
Adds sample e-commerce products to your Supabase database for testing.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database import async_session, Product

# Sample products in Arabic e-commerce context
SAMPLE_PRODUCTS = [
    {
        "name": "قميص قطن أزرق - Blue Cotton Shirt",
        "price": 299.99,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["أزرق", "Blue", "أبيض", "White"],
        "stock_count": 50,
        "description": "قميص قطن عالي الجودة مناسب لجميع المناسبات - High quality cotton shirt suitable for all occasions",
        "is_active": True
    },
    {
        "name": "بنطلون جينز - Denim Jeans",
        "price": 449.99,
        "sizes": ["28", "30", "32", "34", "36"],
        "colors": ["أزرق غامق", "Dark Blue", "أسود", "Black"],
        "stock_count": 35,
        "description": "جينز عصري مريح - Modern comfortable denim jeans",
        "is_active": True
    },
    {
        "name": "فستان صيفي - Summer Dress",
        "price": 599.99,
        "sizes": ["S", "M", "L"],
        "colors": ["أحمر", "Red", "أصفر", "Yellow", "أخضر", "Green"],
        "stock_count": 25,
        "description": "فستان صيفي خفيف ومريح - Light and comfortable summer dress",
        "is_active": True
    },
    {
        "name": "جاكيت جلد - Leather Jacket",
        "price": 899.99,
        "sizes": ["M", "L", "XL"],
        "colors": ["أسود", "Black", "بني", "Brown"],
        "stock_count": 15,
        "description": "جاكيت جلد أصلي فاخر - Premium genuine leather jacket",
        "is_active": True
    },
    {
        "name": "حذاء رياضي - Sports Shoes",
        "price": 399.99,
        "sizes": ["39", "40", "41", "42", "43", "44"],
        "colors": ["أبيض", "White", "أسود", "Black", "رمادي", "Grey"],
        "stock_count": 60,
        "description": "حذاء رياضي مريح للاستخدام اليومي - Comfortable sports shoes for daily use",
        "is_active": True
    },
    {
        "name": "شنطة يد نسائية - Women's Handbag",
        "price": 349.99,
        "sizes": ["One Size"],
        "colors": ["بيج", "Beige", "أسود", "Black", "بني", "Brown"],
        "stock_count": 20,
        "description": "شنطة يد أنيقة مصنوعة من جلد صناعي عالي الجودة - Elegant handbag made of high-quality synthetic leather",
        "is_active": True
    },
    {
        "name": "تيشيرت رياضي - Sports T-Shirt",
        "price": 149.99,
        "sizes": ["S", "M", "L", "XL", "XXL"],
        "colors": ["أبيض", "White", "أسود", "Black", "أزرق", "Blue", "أحمر", "Red"],
        "stock_count": 100,
        "description": "تيشيرت رياضي مصنوع من قماش يسمح بمرور الهواء - Sports t-shirt made of breathable fabric",
        "is_active": True
    },
    {
        "name": "ساعة يد رجالية - Men's Watch",
        "price": 799.99,
        "sizes": ["One Size"],
        "colors": ["فضي", "Silver", "ذهبي", "Gold", "أسود", "Black"],
        "stock_count": 30,
        "description": "ساعة يد رجالية أنيقة مقاومة للماء - Elegant men's watch, water resistant",
        "is_active": True
    },
    {
        "name": "نظارة شمسية - Sunglasses",
        "price": 199.99,
        "sizes": ["One Size"],
        "colors": ["أسود", "Black", "بني", "Brown", "أزرق", "Blue"],
        "stock_count": 45,
        "description": "نظارة شمسية بحماية UV - Sunglasses with UV protection",
        "is_active": True
    },
    {
        "name": "معطف شتوي - Winter Coat",
        "price": 1299.99,
        "sizes": ["M", "L", "XL"],
        "colors": ["أسود", "Black", "رمادي", "Grey", "كحلي", "Navy"],
        "stock_count": 12,
        "description": "معطف شتوي دافئ ومقاوم للماء - Warm winter coat, water resistant",
        "is_active": True
    },
    {
        "name": "Urban Hoodie",
        "price": 45.00,
        "sizes": ["XS", "S", "M", "L", "XL"],
        "colors": ["Heather Grey", "Charcoal", "Olive", "Red"],
        "stock_count": 40,
        "description": "Heavyweight fleece hoodie with a kangaroo pocket. Perfect for layering in colder weather.",
        "is_active": True
    },
    {
        "name": "Classic Cotton T-Shirt",
        "price": 24.99,
        "sizes": ["S", "M", "L", "XL", "XXL"],
        "colors": ["White", "Black", "Navy Blue", "Red"],
        "stock_count": 150,
        "description": "A premium basic t-shirt made from 100% organic cotton. Breathable and perfect for daily wear.",
        "is_active": True
    },
    {
        "name": "Black Leather Jacket",
        "price": 1099.99,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black"],
        "stock_count": 18,
        "description": "Premium black leather jacket with modern fit. Perfect for fall and winter.",
        "is_active": True
    },
    {
        "name": "Slim Fit Jeans",
        "price": 399.99,
        "sizes": ["28", "30", "32", "34", "36"],
        "colors": ["Dark Wash", "Light Wash", "Black"],
        "stock_count": 55,
        "description": "Modern slim fit jeans with stretch for comfort. Perfect for everyday wear.",
        "is_active": True
    },
    {
        "name": "Comfortable Sport Pants",
        "price": 249.99,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black", "Grey", "Navy"],
        "stock_count": 70,
        "description": "Lightweight and breathable sport pants. Perfect for workouts and casual wear.",
        "is_active": True
    },
    {
        "name": "Winter Sweater",
        "price": 349.99,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Charcoal", "Navy", "Burgundy"],
        "stock_count": 35,
        "description": "Warm knit sweater perfect for cold weather. Soft and comfortable.",
        "is_active": True
    },
    {
        "name": "بنطلون كلاسيك أسود - Classic Black Pants",
        "price": 379.99,
        "sizes": ["30", "32", "34", "36", "38"],
        "colors": ["أسود", "Black"],
        "stock_count": 45,
        "description": "بنطلون كلاسيك أسود للعمل والمناسبات - Classic black pants for work and formal occasions",
        "is_active": True
    },
    {
        "name": "هودي رياضي - Athletic Hoodie",
        "price": 299.99,
        "sizes": ["M", "L", "XL", "XXL"],
        "colors": ["أسود", "Black", "رمادي", "Grey", "أزرق", "Blue"],
        "stock_count": 50,
        "description": "هودي رياضي مريح ودافئ - Comfortable and warm athletic hoodie",
        "is_active": True
    },
    {
        "name": "Blue Casual Shirt",
        "price": 229.99,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Light Blue", "Royal Blue"],
        "stock_count": 60,
        "description": "Casual blue shirt perfect for everyday wear. Comfortable cotton blend.",
        "is_active": True
    },
    {
        "name": "Best Seller - Premium Hoodie",
        "price": 499.99,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black", "Grey", "Navy"],
        "stock_count": 80,
        "description": "Our best-selling premium hoodie. Ultra-soft fabric with perfect fit. Customer favorite!",
        "is_active": True
    }
]


async def add_sample_products():
    """Add sample products to the database."""
    print("Adding sample products to database...")

    async with async_session() as session:
        added_count = 0

        for product_data in SAMPLE_PRODUCTS:
            # Check if product already exists by name
            from sqlalchemy import select
            result = await session.execute(
                select(Product).where(Product.name == product_data["name"])
            )
            existing = result.scalar()

            if existing:
                print(f"⊘ Skipping '{product_data['name']}' (already exists)")
                continue

            # Add new product
            product = Product(**product_data)
            session.add(product)
            added_count += 1
            print(f"✓ Added '{product_data['name']}'")

        await session.commit()

        print(f"\n{'='*60}")
        print(f"Summary: Added {added_count} new products")
        print(f"{'='*60}\n")

        # Display all products
        result = await session.execute(select(Product))
        all_products = result.scalars().all()

        print("Current products in database:")
        print(f"{'Name':<40} {'Price':>10} {'Stock':>8}")
        print("-" * 60)
        for p in all_products:
            name_short = p.name[:37] + "..." if len(p.name) > 40 else p.name
            print(f"{name_short:<40} ${p.price:>9.2f} {p.stock_count:>8}")

        print(f"\nTotal: {len(all_products)} products")


async def clear_all_products():
    """Remove all products from database (use with caution!)"""
    print("⚠️  WARNING: This will delete ALL products from the database!")
    response = input("Are you sure? Type 'yes' to confirm: ")

    if response.lower() != 'yes':
        print("Cancelled.")
        return

    async with async_session() as session:
        from sqlalchemy import delete
        result = await session.execute(delete(Product))
        await session.commit()
        print(f"✓ Deleted {result.rowcount} products")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--clear":
        asyncio.run(clear_all_products())
    else:
        asyncio.run(add_sample_products())
        print("\n💡 Tip: Use 'python add_sample_products.py --clear' to remove all products")
