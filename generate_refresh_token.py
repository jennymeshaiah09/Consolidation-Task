"""
Generate Google Ads API Refresh Token
Run this script once to get your refresh token for the .env file.
"""

import os
from dotenv import load_dotenv

def main():
    """Generate refresh token for Google Ads API."""

    print("\n" + "="*70)
    print("Google Ads API - Refresh Token Generator")
    print("="*70)

    # Load credentials from .env file
    load_dotenv()
    client_id = os.getenv('GOOGLE_ADS_CLIENT_ID')
    client_secret = os.getenv('GOOGLE_ADS_CLIENT_SECRET')

    if not client_id or not client_secret:
        print("\n[ERROR] Client ID and Client Secret not found in .env file!")
        print("Please ensure GOOGLE_ADS_CLIENT_ID and GOOGLE_ADS_CLIENT_SECRET are set.")
        return

    print(f"\n[OK] Loaded Client ID: {client_id[:30]}...")
    print(f"[OK] Loaded Client Secret: {client_secret[:15]}...")
    print()

    # Install required package
    print("\n[INSTALL] Installing required package...")
    import subprocess
    import sys
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "google-auth-oauthlib"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        print("[OK] Package installed successfully")
    except subprocess.CalledProcessError:
        print("[WARNING] Could not install package automatically")
        print("Please run: pip install google-auth-oauthlib")
        return

    # Import after installation
    from google_auth_oauthlib.flow import InstalledAppFlow

    # OAuth2 scope for Google Ads API
    SCOPES = ['https://www.googleapis.com/auth/adwords']

    # Create the flow
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8090/"]
            }
        },
        scopes=SCOPES
    )

    print("\n[AUTH] Opening browser for authentication...")
    print("Please sign in and authorize the application.")
    print("Note: The browser will redirect to http://localhost:8090/")
    print()

    try:
        # Run the OAuth flow on port 8090
        credentials = flow.run_local_server(port=8090)

        print("\n" + "="*70)
        print("[SUCCESS] Your refresh token is:")
        print("="*70)
        print(f"\n{credentials.refresh_token}\n")
        print("="*70)
        print("\n[NEXT STEPS]")
        print("1. Copy the token above")
        print("2. Add it to your .env file as GOOGLE_ADS_REFRESH_TOKEN")
        print("3. Run test_google_ads_api.py to verify the setup")
        print("="*70 + "\n")

    except Exception as e:
        print(f"\n[ERROR] Error during authentication: {e}")
        print("\nTroubleshooting:")
        print("- Make sure you're using the correct Client ID and Secret")
        print("- Check that your OAuth consent screen is configured")
        print("- Verify your email is added as a test user")
        return

if __name__ == '__main__':
    main()
