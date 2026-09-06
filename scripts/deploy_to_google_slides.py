"""
DEPLOY_TO_GOOGLE_SLIDES.PY — Deploy MT Deck to Google Slides API
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Purpose:
  Takes a batchUpdate JSON payload (from build_mt_monthly_ppt.py --format json)
  and deploys it to Google Slides via the Slides API.
  Creates new presentation or updates existing one.

Requirements:
  - google-auth-oauthlib (pip install google-auth-oauthlib)
  - google-auth-httplib2 (pip install google-auth-httplib2)
  - google-api-python-client (pip install google-api-python-client)
  - credentials.json (from Google Cloud Console OAuth 2.0 desktop app)

Setup:
  1. Create Google Cloud project
  2. Enable Google Slides API + Google Drive API
  3. Create OAuth 2.0 credentials (Desktop app type)
  4. Download credentials.json to scripts/ directory
  5. Run: python deploy_to_google_slides.py --json-file MT_september2026_gslides_batch.json
     (First run opens browser for OAuth consent; saves token.pickle for future runs)

Usage:
  # Create new presentation
  python deploy_to_google_slides.py --json-file MT_september2026_gslides_batch.json

  # Update existing presentation
  python deploy_to_google_slides.py --json-file MT_september2026_gslides_batch.json \
                                      --presentation-id 1ABC...

  # Dry-run (validate payload without deploying)
  python deploy_to_google_slides.py --json-file MT_september2026_gslides_batch.json \
                                      --dry-run

Author: Claude Haiku 4.5 | Session: MT Intelligence Framework
Date: 09-Sep-2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import argparse
import json
import os
import pickle
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from google.oauth2.credentials import Credentials as UserCredentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError as e:
    print(f"❌ Missing required Google API libraries: {e}")
    print("   Install via: pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client")
    exit(1)

# Google Slides API scopes
SCOPES = ["https://www.googleapis.com/auth/presentations", "https://www.googleapis.com/auth/drive"]

# Credentials file paths
CREDENTIALS_FILE = Path(__file__).parent / "credentials.json"
TOKEN_FILE = Path(__file__).parent / "token.pickle"


def authenticate():
    """Authenticate with Google Slides API using OAuth 2.0."""
    creds = None

    # Load cached token if available
    if TOKEN_FILE.exists():
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    # If no valid credentials, request new ones via OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not CREDENTIALS_FILE.exists():
                raise FileNotFoundError(
                    f"❌ credentials.json not found at {CREDENTIALS_FILE}\n"
                    "   Get it from: Google Cloud Console → OAuth 2.0 Desktop app credentials"
                )
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)

        # Save token for future use
        with open(TOKEN_FILE, "wb") as token:
            pickle.dump(creds, token)

    return creds


def create_presentation(service, title: str) -> str:
    """Create a new Google Slides presentation and return its ID."""
    body = {"title": title}
    presentation = service.presentations().create(body=body).execute()
    presentation_id = presentation.get("presentationId")
    print(f"✓ Created presentation: {presentation_id}")
    return presentation_id


def deploy_batch(
    service,
    presentation_id: str,
    batch_payload: Dict[str, Any],
    dry_run: bool = False
) -> Dict[str, Any]:
    """Deploy batchUpdate operations to Google Slides presentation."""
    if dry_run:
        print(f"📋 [DRY RUN] Would deploy {len(batch_payload.get('requests', []))} requests")
        return {"dry_run": True, "request_count": len(batch_payload.get("requests", []))}

    try:
        # Execute batchUpdate
        response = service.presentations().batchUpdate(
            presentationId=presentation_id,
            body=batch_payload
        ).execute()

        # Count successfully executed requests
        replies = response.get("replies", [])
        print(f"✅ Deployed {len(replies)} operations to {presentation_id}")
        return response
    except HttpError as e:
        print(f"❌ Google Slides API error: {e}")
        raise


def get_presentation_url(presentation_id: str) -> str:
    """Return shareable Google Slides URL."""
    return f"https://docs.google.com/presentation/d/{presentation_id}/edit"


def load_batch_payload(json_file: str) -> Dict[str, Any]:
    """Load batchUpdate payload from JSON file."""
    with open(json_file, "r") as f:
        payload = json.load(f)

    request_count = len(payload.get("requests", []))
    if request_count == 0:
        raise ValueError(f"❌ No requests found in {json_file}")

    print(f"✓ Loaded {request_count} API requests from {json_file}")
    return payload


def main():
    parser = argparse.ArgumentParser(
        description="Deploy MT deck to Google Slides via API"
    )
    parser.add_argument(
        "--json-file",
        required=True,
        help="Path to batchUpdate JSON payload (from build_mt_monthly_ppt.py --format json)"
    )
    parser.add_argument(
        "--presentation-id",
        default=None,
        help="Existing presentation ID (creates new if omitted)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate payload without deploying"
    )
    parser.add_argument(
        "--title",
        default="MT Leadership Deck",
        help="Title for new presentation (default: 'MT Leadership Deck')"
    )

    args = parser.parse_args()

    # Validate JSON file exists
    if not os.path.exists(args.json_file):
        print(f"❌ File not found: {args.json_file}")
        exit(1)

    # Load payload
    print(f"\n📂 Loading {args.json_file}...")
    batch_payload = load_batch_payload(args.json_file)

    # Authenticate
    print("🔐 Authenticating with Google Slides API...")
    creds = authenticate()
    service = build("slides", "v1", credentials=creds)

    # Get or create presentation
    if args.presentation_id:
        presentation_id = args.presentation_id
        print(f"✓ Using existing presentation: {presentation_id}")
    else:
        presentation_id = create_presentation(service, args.title)

    # Deploy
    print(f"\n📤 Deploying to Google Slides...")
    try:
        response = deploy_batch(service, presentation_id, batch_payload, dry_run=args.dry_run)

        if not args.dry_run:
            url = get_presentation_url(presentation_id)
            print(f"\n✨ Presentation ready: {url}")
            print(f"   (May take 10-30s to fully render all content)")
        exit(0)
    except Exception as e:
        print(f"❌ Deployment failed: {e}")
        exit(1)


if __name__ == "__main__":
    main()
