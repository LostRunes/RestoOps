"""
One-time Gmail OAuth2 setup script.

Run this ONCE to get a refresh token for the RestoOps Gmail API integration.

Usage:
    python scripts/gmail_oauth_setup.py

What it does:
    1. Opens your browser to Google's OAuth consent screen
    2. You log in with the Gmail account you want to use for sending
    3. You grant the requested permissions
    4. Prints the refresh token and instructions for updating .env

After running this, copy the GMAIL_REFRESH_TOKEN value into your .env file.
You never need to run this again unless you revoke access or change accounts.
"""

import os
import sys

# Allow running from the repo root or apps/api directory
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from google_auth_oauthlib.flow import InstalledAppFlow

CLIENT_ID = os.getenv("GMAIL_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET", "")

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]


def get_flow():
    # If credentials.json exists locally, prefer loading from it
    credentials_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "credentials.json")
    if os.path.exists("credentials.json"):
        return InstalledAppFlow.from_client_secrets_file("credentials.json", scopes=SCOPES)
    elif os.path.exists(credentials_path):
        return InstalledAppFlow.from_client_secrets_file(credentials_path, scopes=SCOPES)
    elif CLIENT_ID and CLIENT_SECRET:
        client_config = {
            "installed": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            }
        }
        return InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
    else:
        raise ValueError(
            "Missing OAuth credentials. Provide GMAIL_CLIENT_ID & GMAIL_CLIENT_SECRET in environment or place credentials.json in repo root."
        )


def main():
    print("=" * 60)
    print("  RestoOps — Gmail OAuth2 Setup")
    print("=" * 60)
    print()
    print("This will open your browser. Log in with the Gmail account")
    print("you want RestoOps to send emails FROM.")
    print()
    print("Scopes being requested: gmail.modify")
    print("  → Can send, read, and label emails.")
    print("  → Cannot permanently delete emails.")
    print()
    input("Press ENTER to open your browser...")

    flow = get_flow()
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    print()
    print("=" * 60)
    print("  SUCCESS — Your refresh token:")
    print("=" * 60)
    print()
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print()
    print("Add these lines to your C:\\RestoOps\\.env file:")
    print()
    print(f"GMAIL_CLIENT_ID={CLIENT_ID or '<your_client_id>'}")
    print(f"GMAIL_CLIENT_SECRET={CLIENT_SECRET or '<your_client_secret>'}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    print("GMAIL_SENDER_EMAIL=<the gmail address you just logged in with>")
    print()
    print("=" * 60)
    print("Done! You only need to do this once.")
    print("=" * 60)


if __name__ == "__main__":
    main()
