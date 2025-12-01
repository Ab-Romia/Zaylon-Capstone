#!/usr/bin/env python3
"""
Test different Supabase connection URL formats to find which works.
Run this before deploying to Render to verify connection.
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

# Your project info
PROJECT_REF = "evugisirvhbpfdhcztbk"
PASSWORD = "8368@zaylon"  # Will be URL-encoded
PASSWORD_ENCODED = "8368%40zaylon"

# Common regions to try
REGIONS = ["us-east-1", "us-west-1", "eu-west-1", "ap-southeast-1"]

# Test configurations
URLS_TO_TEST = [
    {
        "name": "Current Direct Connection (Your .env)",
        "url": f"postgresql+psycopg://postgres:{PASSWORD_ENCODED}@db.{PROJECT_REF}.supabase.co:5432/postgres"
    },
    {
        "name": "Direct with SSL parameters",
        "url": f"postgresql+psycopg://postgres:{PASSWORD_ENCODED}@db.{PROJECT_REF}.supabase.co:5432/postgres?sslmode=require&connect_timeout=10"
    },
    {
        "name": "Port 6543 (Transaction pooler)",
        "url": f"postgresql+psycopg://postgres:{PASSWORD_ENCODED}@db.{PROJECT_REF}.supabase.co:6543/postgres"
    },
]

# Add pooler URLs for each region
for region in REGIONS:
    URLS_TO_TEST.append({
        "name": f"Pooler - {region} (port 5432)",
        "url": f"postgresql+psycopg://postgres.{PROJECT_REF}:{PASSWORD_ENCODED}@aws-0-{region}.pooler.supabase.com:5432/postgres"
    })
    URLS_TO_TEST.append({
        "name": f"Pooler - {region} (port 6543)",
        "url": f"postgresql+psycopg://postgres.{PROJECT_REF}:{PASSWORD_ENCODED}@aws-0-{region}.pooler.supabase.com:6543/postgres"
    })


async def test_connection(url, timeout=5):
    """Test a single database connection URL."""
    try:
        engine = create_async_engine(
            url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": timeout}
        )

        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT version()"))
            version = result.scalar()
            await engine.dispose()
            return True, version.split(',')[0] if version else "Connected"

    except asyncio.TimeoutError:
        return False, "Connection timeout"
    except Exception as e:
        error_msg = str(e)
        # Shorten error messages
        if "Network is unreachable" in error_msg:
            return False, "Network unreachable (IPv6 issue)"
        elif "could not translate host" in error_msg:
            return False, "Host not found"
        elif "password authentication failed" in error_msg:
            return False, "Authentication failed"
        elif "Connection refused" in error_msg:
            return False, "Connection refused"
        else:
            # Get first line of error
            return False, error_msg.split('\n')[0][:60]


async def test_all():
    """Test all connection URLs."""
    print("=" * 80)
    print("  DATABASE CONNECTION TESTING")
    print("  Testing different Supabase connection formats for Render compatibility")
    print("=" * 80)
    print()

    results = []

    for i, config in enumerate(URLS_TO_TEST, 1):
        print(f"[{i}/{len(URLS_TO_TEST)}] Testing: {config['name']}")
        print(f"     URL: {config['url'][:70]}...")

        success, message = await test_connection(config['url'])

        results.append({
            "name": config['name'],
            "url": config['url'],
            "success": success,
            "message": message
        })

        if success:
            print(f"     ✅ SUCCESS - {message}")
        else:
            print(f"     ❌ FAILED - {message}")

        print()

    # Summary
    print("=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    print()

    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]

    print(f"✅ Successful: {len(successful)}")
    print(f"❌ Failed: {len(failed)}")
    print()

    if successful:
        print("=" * 80)
        print("  ✅ WORKING CONNECTIONS (Use any of these on Render)")
        print("=" * 80)
        print()

        for result in successful:
            print(f"📌 {result['name']}")
            print(f"   {result['url']}")
            print(f"   Info: {result['message']}")
            print()

        print("=" * 80)
        print("  RECOMMENDATION")
        print("=" * 80)
        print()

        # Find best option
        best = successful[0]

        # Prefer pooler over direct
        for r in successful:
            if 'Pooler' in r['name']:
                best = r
                break

        print("Use this DATABASE_URL in Render:")
        print()
        print(best['url'])
        print()
        print(f"Why: {best['name']}")
        print()

    else:
        print("❌ No successful connections found!")
        print()
        print("Troubleshooting:")
        print("1. Check if your Supabase project is active")
        print("2. Verify password is correct")
        print("3. Check Supabase dashboard for connection issues")
        print("4. Try resetting database password in Supabase Settings")
        print()

    print("=" * 80)


if __name__ == "__main__":
    print()
    print("⏳ Testing connections... This may take a minute.")
    print()

    try:
        asyncio.run(test_all())
    except KeyboardInterrupt:
        print("\n\n⚠️  Testing interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error running tests: {e}")
        import traceback
        traceback.print_exc()
