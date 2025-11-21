# Render Deployment IPv6 Fix

## Problem
When deploying to Render, you may encounter this error:
```
sqlalchemy.exc.OperationalError: (psycopg.OperationalError) connection is bad:
connection to server at "2a05:d018:135e:1623:b149:4968:67dc:22c8", port 5432 failed:
Network is unreachable
```

This occurs because:
1. Supabase connection pooler may resolve to IPv6 addresses
2. Render's infrastructure doesn't support IPv6 connections
3. The asyncpg driver attempts to connect via IPv6 and fails

## Solution Implemented

### 1. Automatic IPv4 Resolution (`database.py`)
The application now includes a `force_ipv4_connection_url()` function that:
- Parses your DATABASE_URL
- Resolves hostnames to IPv4 addresses only (using `socket.AF_INET`)
- Reconstructs the connection string with the IPv4 address
- Falls back to original URL if resolution fails
- Logs all resolution steps for debugging

### 2. Enhanced Connection Settings
Added connection arguments to the SQLAlchemy engine:
```python
connect_args={
    "timeout": 30,              # Increase connection timeout
    "command_timeout": 60,      # Command execution timeout
    "server_settings": {
        "application_name": "ecommerce_dm_microservice"
    }
}
```

## Configuration for Supabase

### Required: Use Session Mode (IPv4 Compatible)

1. Go to your Supabase Dashboard
2. Navigate to: **Project Settings > Database > Connection String**
3. Select: **Session Mode** (NOT Transaction Mode)
4. Copy the connection string

### Connection String Format

Your Supabase connection string should look like:
```
postgresql+asyncpg://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres
```

**Key points:**
- Port should be `5432` (Session Mode), NOT `6543` (Transaction Mode)
- Use the pooler hostname: `aws-0-[REGION].pooler.supabase.com`
- Include the `postgresql+asyncpg://` prefix for async support

### Setting Environment Variable on Render

1. Go to your Render dashboard
2. Select your Web Service
3. Go to **Environment** tab
4. Add/Update environment variable:
   - **Key:** `DATABASE_URL`
   - **Value:** Your Supabase Session Mode connection string (see format above)
5. Save changes (this will trigger a redeploy)

## Verification

After deploying with these fixes, check your Render logs for:

```
INFO: Attempting to resolve database hostname: aws-0-us-east-1.pooler.supabase.com
INFO: Resolved aws-0-us-east-1.pooler.supabase.com to IPv4: 54.123.45.67
INFO: Database URL successfully converted to IPv4
INFO: Database initialized
```

If you see IPv6 warnings:
```
WARNING: Detected IPv6 address in connection string: 2a05:d018:...
```

This means your connection string contains an IPv6 address. Follow the configuration steps above to get the correct Session Mode connection string.

## Troubleshooting

### Still Getting IPv6 Errors?

1. **Double-check Supabase pooler mode:**
   - Must be "Session" mode (port 5432)
   - NOT "Transaction" mode (port 6543)

2. **Verify connection string format:**
   ```bash
   # Should contain a hostname, not an IP address
   postgresql+asyncpg://user:pass@aws-0-region.pooler.supabase.com:5432/postgres

   # NOT like this (direct IP):
   postgresql+asyncpg://user:pass@[2a05:d018::1]:5432/postgres
   ```

3. **Check Render logs for DNS resolution:**
   - Look for "Resolved ... to IPv4: ..." messages
   - If resolution fails, you may need to contact Supabase support

4. **Test connection locally:**
   ```bash
   # Test DNS resolution
   nslookup aws-0-us-east-1.pooler.supabase.com

   # Should return IPv4 addresses (A records)
   # If only IPv6 (AAAA records), contact Supabase support
   ```

### Alternative: Use Direct Connection (Not Recommended)

If pooler continues to have issues, you can use Supabase's direct connection:
```
postgresql+asyncpg://postgres:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

**Note:** Direct connections have connection limits and no pooling. Session Mode pooler is recommended.

## Additional Resources

- [Supabase Connection Pooling](https://supabase.com/docs/guides/database/connecting-to-postgres#connection-pooler)
- [Render IPv6 Support](https://render.com/docs/networking)
- [SQLAlchemy Async Engine](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)
