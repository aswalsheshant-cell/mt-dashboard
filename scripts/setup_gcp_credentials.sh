#!/usr/bin/env bash
set -euo pipefail

# Modern Trade Deck Engine — GCP Service Account Provisioning Script
# Sets up OAuth 2.0 credentials for automated Google Slides publishing

PROJECT_ID="${GCP_PROJECT:-MT-Dashboard-Prod}"
SA_NAME="mt-deck-builder"
SA_DISPLAY="MT Deck Builder Engine"
KEY_OUTPUT_DIR="./credentials"
KEY_OUTPUT_PATH="${KEY_OUTPUT_DIR}/service_account.json"

echo "=========================================================="
echo "Modern Trade Deck Engine — GCP Provisioning"
echo "=========================================================="
echo ""

# Step 1: Select Project
echo "Step 1: Configuring Google Cloud project..."
gcloud config set project "${PROJECT_ID}" 2>/dev/null || {
    echo "❌ Project ${PROJECT_ID} not found. Create it manually in console."
    exit 1
}
echo "✓ Project: ${PROJECT_ID}"
echo ""

# Step 2: Enable APIs
echo "Step 2: Enabling required Google Workspace APIs..."
gcloud services enable slides.googleapis.com 2>/dev/null
gcloud services enable drive.googleapis.com 2>/dev/null
echo "✓ Google Slides API enabled"
echo "✓ Google Drive API enabled"
echo ""

# Step 3: Create Service Account
echo "Step 3: Creating service account..."
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

# Check if service account already exists
if gcloud iam service-accounts describe "${SA_EMAIL}" >/dev/null 2>&1; then
    echo "✓ Service account already exists: ${SA_EMAIL}"
else
    gcloud iam service-accounts create "${SA_NAME}" \
        --display-name="${SA_DISPLAY}" \
        --description="Publishes monthly Modern Trade leadership decks to Google Slides" \
        2>/dev/null
    echo "✓ Service account created: ${SA_EMAIL}"
fi
echo ""

# Step 4: Generate JSON Key
echo "Step 4: Generating service account JSON key..."
mkdir -p "${KEY_OUTPUT_DIR}"

# Remove old key if exists
if [ -f "${KEY_OUTPUT_PATH}" ]; then
    echo "  (Replacing existing key)"
fi

gcloud iam service-accounts keys create "${KEY_OUTPUT_PATH}" \
    --iam-account="${SA_EMAIL}" \
    2>/dev/null

chmod 600 "${KEY_OUTPUT_PATH}"
echo "✓ Key saved to: ${KEY_OUTPUT_PATH}"
echo ""

# Step 5: Display Key for GitHub Secrets
echo "=========================================================="
echo "NEXT STEP: Add to GitHub Secrets"
echo "=========================================================="
echo ""
echo "Copy the JSON key below and paste into GitHub:"
echo "  Settings → Secrets and variables → Actions"
echo "  Secret name: GCP_SERVICE_ACCOUNT_KEY"
echo ""
echo "--- BEGIN JSON KEY ---"
cat "${KEY_OUTPUT_PATH}"
echo ""
echo "--- END JSON KEY ---"
echo ""
echo "=========================================================="
echo "✓ GCP Provisioning Complete!"
echo "=========================================================="
