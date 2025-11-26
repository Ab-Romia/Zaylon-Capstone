#!/bin/bash

# Instagram Webhook Setup Diagnostic Script
# This script checks if your Instagram webhook setup is configured correctly

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║   Instagram Webhook Setup Diagnostic Tool                 ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if required tools are installed
echo "Checking prerequisites..."
if ! command -v curl &> /dev/null; then
    print_status 1 "curl is required but not installed"
    exit 1
fi
print_status 0 "curl is installed"

if ! command -v jq &> /dev/null; then
    print_warning "jq not installed - output will be raw JSON (install: apt-get install jq)"
    JQ_INSTALLED=false
else
    print_status 0 "jq is installed"
    JQ_INSTALLED=true
fi
echo ""

# Prompt for configuration
echo "Please provide the following information:"
echo ""

read -p "Facebook Page ID: " PAGE_ID
read -p "Facebook Page Access Token: " PAGE_TOKEN
read -p "Meta App ID: " APP_ID
read -p "n8n Webhook URL (e.g., https://xxx.app.n8n.cloud/webhook/instagram-dm): " WEBHOOK_URL
read -p "Verify Token (from your n8n workflow): " VERIFY_TOKEN

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "Running diagnostics..."
echo "═══════════════════════════════════════════════════════════"
echo ""

# Test 1: Webhook verification
echo "1. Testing n8n webhook verification endpoint..."
CHALLENGE="1234567890"
RESPONSE=$(curl -s "$WEBHOOK_URL?hub.mode=subscribe&hub.verify_token=$VERIFY_TOKEN&hub.challenge=$CHALLENGE")

if [ "$RESPONSE" == "$CHALLENGE" ]; then
    print_status 0 "Webhook verification works correctly"
else
    print_status 1 "Webhook verification FAILED"
    echo "   Expected: $CHALLENGE"
    echo "   Got: $RESPONSE"
    echo "   Check: Is your n8n workflow active? Is verify token correct?"
fi
echo ""

# Test 2: Check Instagram connection
echo "2. Checking if Instagram Business Account is connected to Page..."
if [ "$JQ_INSTALLED" = true ]; then
    IG_RESPONSE=$(curl -s "https://graph.facebook.com/v21.0/$PAGE_ID?fields=instagram_business_account&access_token=$PAGE_TOKEN")
    IG_ACCOUNT_ID=$(echo "$IG_RESPONSE" | jq -r '.instagram_business_account.id // empty')

    if [ -n "$IG_ACCOUNT_ID" ] && [ "$IG_ACCOUNT_ID" != "null" ]; then
        print_status 0 "Instagram Business Account is connected"
        echo "   Instagram Account ID: $IG_ACCOUNT_ID"

        # Get Instagram username
        IG_INFO=$(curl -s "https://graph.facebook.com/v21.0/$IG_ACCOUNT_ID?fields=username,name&access_token=$PAGE_TOKEN")
        IG_USERNAME=$(echo "$IG_INFO" | jq -r '.username // empty')
        IG_NAME=$(echo "$IG_INFO" | jq -r '.name // empty')
        echo "   Username: @$IG_USERNAME"
        echo "   Name: $IG_NAME"
    else
        print_status 1 "Instagram Business Account is NOT connected"
        echo "   Fix: Go to Facebook Page Settings → Instagram → Connect Account"
        echo "   Response: $IG_RESPONSE"
    fi
else
    IG_RESPONSE=$(curl -s "https://graph.facebook.com/v21.0/$PAGE_ID?fields=instagram_business_account&access_token=$PAGE_TOKEN")
    echo "$IG_RESPONSE"
fi
echo ""

# Test 3: Check if page is subscribed to app
echo "3. Checking if Page is subscribed to App webhooks..."
if [ "$JQ_INSTALLED" = true ]; then
    SUBSCRIPTION=$(curl -s "https://graph.facebook.com/v21.0/$PAGE_ID/subscribed_apps?access_token=$PAGE_TOKEN")
    APP_SUBSCRIBED=$(echo "$SUBSCRIPTION" | jq -r ".data[] | select(.id==\"$APP_ID\") | .id")

    if [ "$APP_SUBSCRIBED" == "$APP_ID" ]; then
        print_status 0 "Page IS subscribed to app webhooks"
        SUBSCRIBED_FIELDS=$(echo "$SUBSCRIPTION" | jq -r ".data[] | select(.id==\"$APP_ID\") | .subscribed_fields[]")
        echo "   Subscribed fields:"
        while IFS= read -r field; do
            echo "      - $field"
        done <<< "$SUBSCRIBED_FIELDS"
    else
        print_status 1 "Page is NOT subscribed to app webhooks"
        echo ""
        echo "   ${YELLOW}FIX THIS ISSUE:${NC}"
        echo "   Run this command to subscribe:"
        echo ""
        echo "   curl -X POST \"https://graph.facebook.com/v21.0/$PAGE_ID/subscribed_apps?subscribed_fields=messages,messaging_postbacks&access_token=$PAGE_TOKEN\""
        echo ""
    fi
else
    SUBSCRIPTION=$(curl -s "https://graph.facebook.com/v21.0/$PAGE_ID/subscribed_apps?access_token=$PAGE_TOKEN")
    echo "$SUBSCRIPTION"
fi
echo ""

# Test 4: Check token permissions
echo "4. Checking Page Access Token permissions..."
if [ "$JQ_INSTALLED" = true ]; then
    TOKEN_INFO=$(curl -s "https://graph.facebook.com/v21.0/me/permissions?access_token=$PAGE_TOKEN")

    REQUIRED_PERMS=("pages_messaging" "pages_manage_metadata" "instagram_basic" "instagram_manage_messages")
    ALL_GRANTED=true

    for perm in "${REQUIRED_PERMS[@]}"; do
        STATUS=$(echo "$TOKEN_INFO" | jq -r ".data[] | select(.permission==\"$perm\") | .status")
        if [ "$STATUS" == "granted" ]; then
            print_status 0 "$perm: granted"
        else
            print_status 1 "$perm: NOT granted"
            ALL_GRANTED=false
        fi
    done

    if [ "$ALL_GRANTED" = false ]; then
        echo ""
        echo "   ${YELLOW}Missing permissions!${NC}"
        echo "   Go to Graph API Explorer and generate a new token with all required permissions"
    fi
else
    TOKEN_INFO=$(curl -s "https://graph.facebook.com/v21.0/me/permissions?access_token=$PAGE_TOKEN")
    echo "$TOKEN_INFO"
fi
echo ""

# Test 5: Check token expiration
echo "5. Checking token expiration..."
if [ "$JQ_INSTALLED" = true ]; then
    DEBUG_TOKEN=$(curl -s "https://graph.facebook.com/v21.0/debug_token?input_token=$PAGE_TOKEN&access_token=$PAGE_TOKEN")
    IS_VALID=$(echo "$DEBUG_TOKEN" | jq -r '.data.is_valid')
    EXPIRES_AT=$(echo "$DEBUG_TOKEN" | jq -r '.data.expires_at')

    if [ "$IS_VALID" == "true" ]; then
        print_status 0 "Token is valid"
        if [ "$EXPIRES_AT" != "0" ] && [ "$EXPIRES_AT" != "null" ]; then
            EXPIRY_DATE=$(date -d "@$EXPIRES_AT" 2>/dev/null || date -r "$EXPIRES_AT" 2>/dev/null)
            echo "   Expires: $EXPIRY_DATE"

            CURRENT=$(date +%s)
            DAYS_LEFT=$(( ($EXPIRES_AT - $CURRENT) / 86400 ))
            if [ $DAYS_LEFT -lt 7 ]; then
                print_warning "Token expires in $DAYS_LEFT days! Exchange for long-lived token"
            else
                echo "   Days remaining: $DAYS_LEFT"
            fi
        else
            echo "   Token does not expire (long-lived)"
        fi
    else
        print_status 1 "Token is INVALID"
        echo "   Generate a new token in Graph API Explorer"
    fi
else
    DEBUG_TOKEN=$(curl -s "https://graph.facebook.com/v21.0/debug_token?input_token=$PAGE_TOKEN&access_token=$PAGE_TOKEN")
    echo "$DEBUG_TOKEN"
fi
echo ""

# Summary
echo "═══════════════════════════════════════════════════════════"
echo "Summary & Next Steps"
echo "═══════════════════════════════════════════════════════════"
echo ""

if [ "$APP_SUBSCRIBED" != "$APP_ID" ]; then
    echo "${RED}CRITICAL ISSUE:${NC} Page is not subscribed to app webhooks!"
    echo ""
    echo "This is the #1 reason webhooks don't work. Fix it by running:"
    echo ""
    echo "  curl -X POST \\"
    echo "    \"https://graph.facebook.com/v21.0/$PAGE_ID/subscribed_apps?subscribed_fields=messages,messaging_postbacks&access_token=$PAGE_TOKEN\""
    echo ""
else
    echo "${GREEN}Page subscription:${NC} OK"
fi

if [ -z "$IG_ACCOUNT_ID" ] || [ "$IG_ACCOUNT_ID" == "null" ]; then
    echo "${RED}CRITICAL ISSUE:${NC} Instagram not connected to Page!"
    echo "  Fix: Facebook Page Settings → Instagram → Connect Account"
    echo ""
else
    echo "${GREEN}Instagram connection:${NC} OK"
fi

if [ "$RESPONSE" != "$CHALLENGE" ]; then
    echo "${RED}ISSUE:${NC} Webhook verification failing"
    echo "  Check: n8n workflow is active and verify token matches"
    echo ""
else
    echo "${GREEN}Webhook verification:${NC} OK"
fi

echo ""
echo "After fixing issues, test by:"
echo "1. Login to Instagram with test user"
echo "2. Send DM to your business page: @$IG_USERNAME"
echo "3. Check n8n executions for webhook trigger"
echo ""
echo "For detailed troubleshooting, see:"
echo "INSTAGRAM_WEBHOOK_TROUBLESHOOTING.md"
echo ""
