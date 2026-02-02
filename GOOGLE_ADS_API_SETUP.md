# Google Ads API Setup Guide
Complete guide to set up Google Keyword Planner API for MSV data lookup.

---

## Overview
The Google Ads API provides free access to Keyword Planner data (Monthly Search Volume). You'll need:
- Google Ads Account (free, no ad spend required)
- Google Cloud Project (free tier)
- Developer Token (approval takes 1-2 business days)
- OAuth 2.0 credentials

**Total Setup Time:** ~30 minutes + 1-2 days for approval

---

## Step 1: Create Google Ads Account

### 1.1 Sign Up
1. Go to [Google Ads](https://ads.google.com/)
2. Click **"Start Now"**
3. Sign in with your Google account
4. **IMPORTANT:** Choose **"Switch to Expert Mode"** at the bottom
   - This skips the campaign creation wizard
   - You don't need to create any campaigns or spend money

### 1.2 Complete Account Setup
1. Fill in basic business information:
   - Business name: Your company/project name
   - Website: Optional (can skip)
2. Choose billing country
3. Select timezone and currency
4. **Skip campaign creation** - Click "Submit" without creating ads

### 1.3 Get Your Customer ID
1. Once logged into Google Ads dashboard
2. Look at the top right corner
3. You'll see a **10-digit number** like `123-456-7890`
4. **Save this** - this is your `GOOGLE_ADS_CUSTOMER_ID`
5. Remove the dashes: `1234567890` (use this format in .env)

✅ **Checkpoint:** You should now have a Google Ads account with a Customer ID

---

## Step 2: Create Google Cloud Project

### 2.1 Go to Google Cloud Console
1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with the same Google account
3. Accept Terms of Service if prompted

### 2.2 Create New Project
1. Click the **project dropdown** at the top (says "Select a project")
2. Click **"New Project"**
3. Enter project name: `product-msv-lookup` (or any name)
4. Click **"Create"**
5. Wait for project creation (~30 seconds)
6. Select your new project from the dropdown

✅ **Checkpoint:** You should see your project name in the top bar

---

## Step 3: Enable Google Ads API

### 3.1 Enable the API
1. In Google Cloud Console, go to **"APIs & Services" > "Library"**
   - Or visit: https://console.cloud.google.com/apis/library
2. Search for **"Google Ads API"**
3. Click on **"Google Ads API"**
4. Click **"Enable"**
5. Wait for activation (~10 seconds)

✅ **Checkpoint:** You should see "API enabled" with a green checkmark

---

## Step 4: Create OAuth 2.0 Credentials

### 4.1 Configure OAuth Consent Screen
1. Go to **"APIs & Services" > "OAuth consent screen"**
   - Or visit: https://console.cloud.google.com/apis/credentials/consent
2. Choose **"External"** (unless you have Google Workspace)
3. Click **"Create"**

4. Fill in App Information:
   - **App name:** `Product MSV Lookup` (or any name)
   - **User support email:** Your email
   - **Developer contact email:** Your email
   - Leave other fields blank
5. Click **"Save and Continue"**

6. **Scopes** screen:
   - Click **"Add or Remove Scopes"**
   - Search for `adwords`
   - Select **`https://www.googleapis.com/auth/adwords`**
   - Click **"Update"**
   - Click **"Save and Continue"**

7. **Test Users** screen:
   - Click **"Add Users"**
   - Enter your Google email address
   - Click **"Add"**
   - Click **"Save and Continue"**

8. Review and click **"Back to Dashboard"**

### 4.2 Create OAuth Client ID
1. Go to **"APIs & Services" > "Credentials"**
   - Or visit: https://console.cloud.google.com/apis/credentials
2. Click **"+ Create Credentials"** at the top
3. Select **"OAuth client ID"**
4. Choose application type: **"Desktop app"**
5. Name it: `Desktop Client for MSV Lookup`
6. Click **"Create"**

### 4.3 Download Credentials
1. A popup will show your Client ID and Client Secret
2. Click **"Download JSON"**
3. **Save this file** - you'll need it later
4. Or copy these values:
   - **Client ID:** Something like `123456789-abc123.apps.googleusercontent.com`
   - **Client Secret:** Something like `GOCSPX-abc123xyz789`

✅ **Checkpoint:** You should have `client_id` and `client_secret` saved

---

## Step 5: Apply for Developer Token

### 5.1 Request Developer Token
1. Go back to [Google Ads](https://ads.google.com/)
2. Click **Tools & Settings** icon (wrench) in top right
3. Under **Setup**, click **"API Center"**
4. You'll see **"Developer token"** section
5. Fill in the application form:
   - **API usage:** Select "Basic Access" (sufficient for most use cases)
   - **Primary use case:** "Keyword research and search volume analysis"
   - **Will you be managing campaigns?** Select "No"
   - **Approximate number of API calls:** "Less than 10,000 per day"
6. Click **"Submit"**

### 5.2 Initial Token (Test Mode)
- You'll immediately get a **test developer token** (looks like `a1b2c3d4e5f6g7h8`)
- **Save this** - this is your `GOOGLE_ADS_DEVELOPER_TOKEN`
- Status will show as **"Pending"** or **"Test"**

### 5.3 Wait for Approval (1-2 Business Days)
- Google will review your application
- You'll receive an email when approved
- For Keyword Planner API, **test mode is often sufficient**
- Approved token works the same, just with higher rate limits

✅ **Checkpoint:** You should have a developer token (even if in test mode)

---

## Step 6: Generate Refresh Token

This is the trickiest part - you need to authorize your app and get a refresh token.

### 6.1 Install Google Ads Python Library (Temporary)
```bash
pip install google-ads
```

### 6.2 Create Configuration File
Create a file named `google-ads.yaml` in your project root:

```yaml
developer_token: YOUR_DEVELOPER_TOKEN_HERE
client_id: YOUR_CLIENT_ID_HERE.apps.googleusercontent.com
client_secret: YOUR_CLIENT_SECRET_HERE
refresh_token:
login_customer_id: YOUR_CUSTOMER_ID_HERE
```

Replace:
- `YOUR_DEVELOPER_TOKEN_HERE` - From Step 5
- `YOUR_CLIENT_ID_HERE` - From Step 4.3
- `YOUR_CLIENT_SECRET_HERE` - From Step 4.3
- `YOUR_CUSTOMER_ID_HERE` - From Step 1.3 (10 digits, no dashes)

### 6.3 Run Authentication Script
Create a Python script `generate_refresh_token.py`:

```python
from google_auth_oauthlib.flow import InstalledAppFlow

# OAuth2 scope for Google Ads API
SCOPES = ['https://www.googleapis.com/auth/adwords']

def main():
    # Create the flow using your client_id and client_secret
    flow = InstalledAppFlow.from_client_config(
        {
            "installed": {
                "client_id": "YOUR_CLIENT_ID_HERE.apps.googleusercontent.com",
                "client_secret": "YOUR_CLIENT_SECRET_HERE",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost"]
            }
        },
        scopes=SCOPES
    )

    # Run the OAuth flow
    credentials = flow.run_local_server(port=0)

    print("\n" + "="*60)
    print("SUCCESS! Your refresh token is:")
    print("="*60)
    print(f"\n{credentials.refresh_token}\n")
    print("="*60)
    print("\nCopy this token to your .env file as GOOGLE_ADS_REFRESH_TOKEN")
    print("="*60)

if __name__ == '__main__':
    # Install required package first
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "google-auth-oauthlib"])

    main()
```

Replace `YOUR_CLIENT_ID_HERE` and `YOUR_CLIENT_SECRET_HERE` with your values.

### 6.4 Run the Script
```bash
python generate_refresh_token.py
```

This will:
1. Open your browser
2. Ask you to sign in to Google
3. Show a consent screen asking to access Google Ads data
4. Click **"Allow"**
5. Print your **refresh_token** in the terminal

### 6.5 Save the Refresh Token
Copy the long string (looks like `1//abc123xyz789...`) and save it.

✅ **Checkpoint:** You should now have a `refresh_token`

---

## Step 7: Configure Environment Variables

### 7.1 Update Your `.env` File
Add these new variables to your `.env` file:

```bash
# Existing Gemini API
GOOGLE_API_KEY=your_existing_gemini_key_here

# Google Ads API Credentials
GOOGLE_ADS_DEVELOPER_TOKEN=a1b2c3d4e5f6g7h8
GOOGLE_ADS_CLIENT_ID=123456789-abc123.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=GOCSPX-abc123xyz789
GOOGLE_ADS_REFRESH_TOKEN=1//abc123xyz789...
GOOGLE_ADS_CUSTOMER_ID=1234567890
```

### 7.2 Update `.env.example`
Add these placeholders:

```bash
# Google Gemini API (for keyword generation)
GOOGLE_API_KEY=your_google_gemini_api_key_here

# Google Ads API (for MSV lookup)
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token_here
GOOGLE_ADS_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your_client_secret_here
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token_here
GOOGLE_ADS_CUSTOMER_ID=1234567890
```

✅ **Checkpoint:** Your `.env` file should have all 5 Google Ads credentials

---

## Step 8: Test the API Connection

### 8.1 Install Google Ads Library
Add to `requirements.txt`:
```txt
google-ads>=24.0.0
```

Install:
```bash
pip install google-ads
```

### 8.2 Create Test Script
Create `test_google_ads_api.py`:

```python
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import os
from dotenv import load_dotenv

load_dotenv()

def test_connection():
    """Test Google Ads API connection and list accessible customers."""

    credentials = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
        "use_proto_plus": True
    }

    try:
        client = GoogleAdsClient.load_from_dict(credentials)
        customer_service = client.get_service("CustomerService")

        accessible_customers = customer_service.list_accessible_customers()
        print("✅ API Connection Successful!")
        print(f"\nAccessible customer IDs:")
        for customer in accessible_customers.resource_names:
            print(f"  - {customer}")

        return True

    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error:")
        for error in ex.failure.errors:
            print(f"  - {error.message}")
        return False
    except Exception as ex:
        print(f"❌ Error: {ex}")
        return False

if __name__ == "__main__":
    test_connection()
```

### 8.3 Run Test
```bash
python test_google_ads_api.py
```

Expected output:
```
✅ API Connection Successful!

Accessible customer IDs:
  - customers/1234567890
```

✅ **Checkpoint:** API connection is working!

---

## Step 9: Test Keyword Planner API

### 9.1 Create Keyword Planner Test Script
Create `test_keyword_planner.py`:

```python
from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException
import os
from dotenv import load_dotenv

load_dotenv()

def get_keyword_ideas(keyword_texts):
    """Get keyword ideas with search volume data."""

    credentials = {
        "developer_token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "client_id": os.getenv("GOOGLE_ADS_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_ADS_CLIENT_SECRET"),
        "refresh_token": os.getenv("GOOGLE_ADS_REFRESH_TOKEN"),
        "login_customer_id": os.getenv("GOOGLE_ADS_CUSTOMER_ID"),
        "use_proto_plus": True
    }

    try:
        client = GoogleAdsClient.load_from_dict(credentials)
        keyword_plan_idea_service = client.get_service("KeywordPlanIdeaService")

        # Set up the request
        request = client.get_type("GenerateKeywordIdeasRequest")
        request.customer_id = os.getenv("GOOGLE_ADS_CUSTOMER_ID")

        # Location: United States (2840)
        request.geo_target_constants.append(
            "geoTargetConstants/2840"
        )

        # Language: English (1000)
        request.language = "languageConstants/1000"

        # Keywords to get ideas for
        request.keyword_seed.keywords.extend(keyword_texts)

        # Make the request
        response = keyword_plan_idea_service.generate_keyword_ideas(request=request)

        print("✅ Keyword Planner API Working!\n")
        print(f"{'Keyword':<30} {'Avg Monthly Searches':<20} {'Competition'}")
        print("-" * 70)

        for idea in response:
            keyword = idea.text
            avg_monthly_searches = idea.keyword_idea_metrics.avg_monthly_searches
            competition = idea.keyword_idea_metrics.competition.name
            print(f"{keyword:<30} {avg_monthly_searches:<20} {competition}")

        return True

    except GoogleAdsException as ex:
        print(f"❌ Google Ads API Error:")
        for error in ex.failure.errors:
            print(f"  - {error.message}")
        return False
    except Exception as ex:
        print(f"❌ Error: {ex}")
        return False

if __name__ == "__main__":
    # Test with some sample keywords
    test_keywords = ["wine", "whisky", "dog food", "smartphone"]
    get_keyword_ideas(test_keywords)
```

### 9.2 Run Test
```bash
python test_keyword_planner.py
```

Expected output:
```
✅ Keyword Planner API Working!

Keyword                        Avg Monthly Searches     Competition
----------------------------------------------------------------------
wine                           1000000                  HIGH
red wine                       550000                   MEDIUM
whisky                         450000                   MEDIUM
dog food                       823000                   HIGH
smartphone                     2740000                  HIGH
```

✅ **Success!** You're now ready to integrate MSV lookup into your app!

---

## Troubleshooting

### Error: "Developer token is not approved"
- **Solution:** Your token is in test mode, which is fine for Keyword Planner
- You can still use it, just with lower rate limits
- For production, wait for approval email

### Error: "PERMISSION_DENIED"
- **Solution:** Make sure your OAuth consent screen has the correct scope
- Verify you're using the same Google account for everything
- Check that your email is added as a test user

### Error: "Customer ID not found"
- **Solution:** Remove dashes from Customer ID (use `1234567890` not `123-456-7890`)
- Make sure you're using the right Google Ads account

### Error: "Invalid refresh token"
- **Solution:** Re-run the `generate_refresh_token.py` script
- Make sure you copied the entire token (it's very long)
- Check for extra spaces or newlines

### Browser doesn't open during OAuth flow
- **Solution:** Manually copy the URL from terminal and paste in browser
- Make sure port is not blocked by firewall

---

## Summary Checklist

Before moving to implementation, verify you have:

- [ ] Google Ads account created
- [ ] Customer ID saved (10 digits, no dashes)
- [ ] Google Cloud Project created
- [ ] Google Ads API enabled
- [ ] OAuth consent screen configured
- [ ] OAuth Client ID and Secret obtained
- [ ] Developer Token received (even if pending approval)
- [ ] Refresh Token generated
- [ ] All 5 credentials added to `.env` file
- [ ] `test_google_ads_api.py` runs successfully
- [ ] `test_keyword_planner.py` returns MSV data

---

## Next Steps

Once all credentials are set up:

1. ✅ **Test API connection** - Run both test scripts
2. 🔨 **Implement MSV module** - Create `src/msv_lookup.py`
3. 🔗 **Integrate with pipeline** - Update consolidation flow
4. 📊 **Calculate Peak Seasonality** - Use historical MSV trends
5. 🚀 **Production testing** - Run with real product data

---

## Useful Links

- [Google Ads API Documentation](https://developers.google.com/google-ads/api/docs/start)
- [Keyword Planning Overview](https://developers.google.com/google-ads/api/docs/keyword-planning/overview)
- [Python Client Library](https://github.com/googleads/google-ads-python)
- [OAuth 2.0 Setup Guide](https://developers.google.com/google-ads/api/docs/oauth/overview)
- [API Support Forum](https://groups.google.com/g/adwords-api)

---

**Questions or issues?** Create an issue in your project repository or check the Google Ads API support forum.
