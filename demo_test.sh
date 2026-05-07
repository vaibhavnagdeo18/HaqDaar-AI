#!/bin/bash

# GhostWriter AI (Haqdaar) End-to-End Demo Script
# Simulates a full family journey via WhatsApp Webhook

PHONE="919876543210"
URL="http://localhost:8000/webhook/whatsapp"

send_msg() {
    echo "Sending: $1"
    curl -s -X POST "$URL" \
        -H "Content-Type: application/json" \
        -d "{
          \"object\": \"whatsapp_business_account\",
          \"entry\": [{
            \"changes\": [{
              \"value\": {
                \"messages\": [{
                  \"from\": \"$PHONE\",
                  \"type\": \"text\",
                  \"text\": { \"body\": \"$1\" }
                }]
              }
            }]
          }]
        }" > /dev/null
    sleep 2
}

send_image() {
    echo "Sending Image (ID: $1)"
    curl -s -X POST "$URL" \
        -H "Content-Type: application/json" \
        -d "{
          \"object\": \"whatsapp_business_account\",
          \"entry\": [{
            \"changes\": [{
              \"value\": {
                \"messages\": [{
                  \"from\": \"$PHONE\",
                  \"type\": \"image\",
                  \"image\": { \"id\": \"$1\" }
                }]
              }
            }]
          }]
        }" > /dev/null
    sleep 2
}

echo "--- STARTING GHOSTWRITER AI DEMO ---"

echo "Step 1: Initiation"
send_msg "hi"

echo "Step 2: Onboarding - Language (1 for Telugu)"
send_msg "1"

echo "Step 3: Onboarding - Breadwinner Name"
send_msg "Late Ramesh Kumar"

echo "Step 4: Onboarding - Date of Death"
send_msg "15/08/2023"

echo "Step 5: Onboarding - Employment Type (1 for Government)"
send_msg "1"

echo "Step 6: Onboarding - EPF Status (1 for Yes)"
send_msg "1"

echo "Step 7: Onboarding - State (1 for Telangana)"
echo "This will trigger Compliance Agent (100/100) and Entitlement Agent."
send_msg "1"

echo "Step 8: Requesting EPF Form 20"
send_msg "FILE CLAIM"

echo "Step 9: Uploading Death Certificate for Dispute Analysis"
send_image "death_cert_001"

echo "Step 10: Identity Reconciliation Check (Aadhaar vs Death Certificate)"
send_msg "Aadhaar name is Ramesh K and Death Certificate name is Ramesh Kumar"

echo "--- DEMO COMPLETE ---"
echo "Check Admin Dashboard at http://localhost:8000/dashboard"
echo "Check API Details at http://localhost:8000/api/cases/$PHONE"
