#!/usr/bin/env python3
"""
One-time OAuth setup script for Google Calendar/Meet integration.
Run this OUTSIDE of Docker on your local machine.

Usage:
    python3 setup_google_oauth.py
"""

import pickle
import os

def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("Installing required packages...")
        os.system("pip3 install google-auth-oauthlib google-auth google-api-python-client")
        from google_auth_oauthlib.flow import InstalledAppFlow
    
    SCOPES = ['https://www.googleapis.com/auth/calendar.events']
    
    # Check for credentials file
    if not os.path.exists('credentials.json'):
        print("❌ Error: credentials.json not found!")
        print("Please download OAuth credentials from Google Cloud Console:")
        print("1. Go to https://console.cloud.google.com/apis/credentials")
        print("2. Create OAuth 2.0 Client ID (type: Desktop App)")
        print("3. Download JSON and save as 'credentials.json'")
        return
    
    print("🔐 Starting Google OAuth authentication...")
    print("A browser window will open. Please sign in and authorize the app.")
    
    flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
    creds = flow.run_local_server(port=0)
    
    # Save the credentials
    with open('token.pickle', 'wb') as token:
        pickle.dump(creds, token)
    
    print("\n✅ Authentication successful!")
    print("📁 Token saved to: token.pickle")
    print("\n📋 Next steps:")
    print("1. Rebuild Docker: docker-compose up -d --build")
    print("2. Try scheduling an interview - it should now create real Google Meet links!")

if __name__ == "__main__":
    main()
