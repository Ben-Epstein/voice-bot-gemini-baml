# Quick Start Guide

Get the voice bot running in 5 minutes!

## Prerequisites

- Python 3.11+
- Modal account (https://modal.com)
- Twilio account (https://www.twilio.com)
- Google Gemini API key (https://ai.google.dev)

## Step 1: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Modal

```bash
# Install and authenticate Modal
modal token new
```

## Step 3: Create Secrets

```bash
# Gemini API Key
modal secret create gemini-api-key GEMINI_API_KEY=your_gemini_key_here

# Twilio Credentials
modal secret create twilio-credentials \
  TWILIO_ACCOUNT_SID=your_twilio_sid \
  TWILIO_AUTH_TOKEN=your_twilio_token
```

## Step 4: Deploy to Modal

```bash
modal deploy app.py
```

**Copy the URL from the output!** It will look like:
```
https://your-username--voice-bot-gemini-baml-fastapi-app.modal.run
```

## Step 5: Configure Twilio

1. Go to [Twilio Console](https://console.twilio.com/)
2. Navigate to: Phone Numbers → Manage → Active Numbers
3. Click your phone number
4. Under "Voice & Fax" → "A Call Comes In":
   - Select: **Webhook**
   - URL: `https://your-modal-url/webhook` (from Step 4)
   - HTTP Method: **POST**
5. Click **Save**

## Step 6: Make a Test Call

Call your Twilio phone number and try:
- "What cars do you have available?"
- "How much is the economy car?"
- "I need an SUV for this weekend"

## Viewing Saved Profiles

```bash
# List all profiles
modal volume ls voice-bot-profiles profiles/

# Download a specific profile
modal volume get voice-bot-profiles profiles/profile_CA123_20240115_103000.json ./local-profile.json

# View profile
cat ./local-profile.json | jq .
```

## Testing Locally

For local development (without Modal):

```bash
# Set environment variables
export GEMINI_API_KEY=your_key
export TWILIO_ACCOUNT_SID=your_sid
export TWILIO_AUTH_TOKEN=your_token

# Run locally
python app.py
```

Use [ngrok](https://ngrok.com/) to expose local server:
```bash
ngrok http 8000
```

Then update Twilio webhook to ngrok URL.

## Troubleshooting

### "No module named 'modal'"
```bash
pip install modal
```

### "Secret not found"
Make sure you created the secrets:
```bash
modal secret list
```

### Webhook not working
- Verify URL in Twilio console
- Check Modal logs: `modal app logs voice-bot-gemini-baml`
- Ensure webhook URL ends with `/webhook`

### Need Help?
Check the [SETUP.md](SETUP.md) and [ARCHITECTURE.md](ARCHITECTURE.md) guides for detailed information.
