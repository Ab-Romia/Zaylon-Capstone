#!/usr/bin/env python3
"""
Helper script to convert Supabase connection string for Render deployment.
Handles IPv6 issues by using connection pooler and URL encoding.
"""
from urllib.parse import quote_plus

def convert_to_render_url(supabase_url):
    """
    Convert Supabase connection string to Render-compatible format.

    Args:
        supabase_url: Supabase connection string (direct or pooler)

    Returns:
        Properly formatted connection string for Render
    """
    # Remove protocol if present
    if '://' in supabase_url:
        protocol, rest = supabase_url.split('://', 1)
    else:
        rest = supabase_url

    # Parse connection string parts
    # Format: user:password@host:port/database
    if '@' not in rest:
        print("[ERROR] Invalid connection string format")
        return None

    auth, host_part = rest.split('@', 1)
    user, password = auth.split(':', 1) if ':' in auth else (auth, '')

    if '/' in host_part:
        host_port, database = host_part.rsplit('/', 1)
    else:
        host_port = host_part
        database = 'postgres'

    if ':' in host_port:
        host, port = host_port.rsplit(':', 1)
    else:
        host = host_port
        port = '5432'

    # Check if using pooler (recommended for Render)
    is_pooler = 'pooler' in host

    # URL encode password
    encoded_password = quote_plus(password)

    # Build Render-compatible URL
    render_url = f"postgresql+psycopg://{user}:{encoded_password}@{host}:{port}/{database}"

    return render_url, is_pooler, password != encoded_password


def main():
    print("=" * 70)
    print("  Supabase → Render Database URL Converter")
    print("=" * 70)
    print()

    print("📋 Instructions:")
    print("1. Go to Supabase Dashboard → Settings → Database")
    print("2. Find 'Connection Pooling' section")
    print("3. Copy the 'Session mode' connection string")
    print("4. Paste it below")
    print()
    print("Example pooler URL:")
    print("postgresql://postgres.abc:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres")
    print()
    print("-" * 70)

    # Get input
    supabase_url = input("\nPaste your Supabase connection string: ").strip()

    if not supabase_url:
        print("[ERROR] No URL provided")
        return

    # Convert
    result = convert_to_render_url(supabase_url)

    if not result:
        return

    render_url, is_pooler, password_encoded = result

    print("\n" + "=" * 70)
    print("  [OK] Conversion Complete!")
    print("=" * 70)
    print()

    if not is_pooler:
        print("[WARNING]  WARNING: This is NOT a pooler connection!")
        print("   For Render, you should use the Connection Pooler endpoint.")
        print("   Go to Supabase → Settings → Database → Connection Pooling")
        print()

    if password_encoded:
        print("[OK] Password special characters were URL-encoded")
        print()

    print("🔗 Use this DATABASE_URL in Render:")
    print()
    print(render_url)
    print()

    # Additional info
    print("-" * 70)
    print("📝 Notes:")
    print()

    if is_pooler:
        print("[OK] Using Connection Pooler (Recommended for Render)")
        print("   - Port 6543 (pooler) instead of 5432 (direct)")
        print("   - Better performance and IPv4 compatibility")
    else:
        print("[WARNING]  Using Direct Connection")
        print("   - May have IPv6 issues on Render")
        print("   - Recommend switching to Connection Pooler")

    print()
    print(" Next Steps:")
    print("1. Copy the DATABASE_URL above")
    print("2. Go to Render Dashboard → Your Service → Environment")
    print("3. Add/Update DATABASE_URL environment variable")
    print("4. Redeploy your service")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
