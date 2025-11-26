# Setup Guide

## Prerequisites

1. **Python 3.11+**
2. **Modal Account**: Sign up at https://modal.com
3. **Twilio Account**: Sign up at https://www.twilio.com
4. **Google Gemini API Key**: Get from https://ai.google.dev

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/Ben-Epstein/voice-bot-gemini-baml.git
cd voice-bot-gemini-baml
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up Modal

```bash
# Install Modal CLI
pip install modal

# Authenticate with Modal
modal token new
```

### 4. Create Modal Secrets

Create secrets in your Modal dashboard or via CLI:

```bash
# Gemini API Key
modal secret create gemini-api-key GEMINI_API_KEY=your_api_key_here

# Twilio Credentials
modal secret create twilio-credentials \
  TWILIO_ACCOUNT_SID=your_account_sid \
  TWILIO_AUTH_TOKEN=your_auth_token
```

### 5. Deploy to Modal

```bash
modal deploy app.py
```

This will output a URL like: `https://your-username--voice-bot-gemini-baml-fastapi-app.modal.run`

**Important:** Copy this URL and update the Modal secret for WebSocket connections:

```bash
# Convert HTTP URL to WebSocket URL (https -> wss)
modal secret create modal-config \
  MODAL_WEBSOCKET_URL=wss://your-username--voice-bot-gemini-baml-fastapi-app.modal.run
```

Then add this secret to the app.py function decorator (add to secrets list).

### 6. Configure Twilio

1. Go to your Twilio Console
2. Navigate to Phone Numbers > Manage > Active Numbers
3. Click on your phone number
4. Under "Voice & Fax", set:
   - **A Call Comes In**: Webhook
   - **URL**: `https://your-modal-url/webhook` (from step 5)
   - **HTTP Method**: POST

### 7. Test the Application

Call your Twilio phone number and interact with the voice bot!

## Local Development

For local testing without Modal:

```bash
# Set environment variables
export GEMINI_API_KEY=your_api_key
export TWILIO_ACCOUNT_SID=your_account_sid
export TWILIO_AUTH_TOKEN=your_auth_token

# Run locally
python app.py
```

Note: For local development with Twilio, you'll need to use ngrok or similar to expose your local server:

```bash
ngrok http 8000
```

Then update your Twilio webhook URL to the ngrok URL.

## BAML Integration

The BAML functions are defined in `baml_src/main.baml`. To regenerate the BAML client code:

```bash
baml generate
```

This creates Python client code in `baml_client/` directory that can be imported and used in the application.

## Viewing Saved Profiles

Renter profiles are saved in the Modal volume at `/profiles/`. To view them:

```bash
# List profiles
modal volume ls voice-bot-profiles profiles/

# Download a profile
modal volume get voice-bot-profiles profiles/profile_CA1234_20240101_120000.json
```

## Troubleshooting

### Webhook not receiving calls

- Verify your Twilio webhook URL is correct
- Check Modal deployment logs: `modal app logs voice-bot-gemini-baml`
- Ensure the webhook endpoint is publicly accessible

### Gemini API errors

- Verify your API key is correct
- Check you have sufficient quota
- Review Modal logs for detailed error messages

### WebSocket connection issues

- Ensure the WebSocket URL in the TwiML response matches your Modal deployment
- Check for any firewall or network restrictions
- Review browser/Twilio console for connection errors

## Architecture Overview

```
Incoming Call (Twilio)
    ↓
Webhook (/webhook)
    ↓
TwiML Response with WebSocket URL
    ↓
WebSocket Connection (/ws/{call_sid})
    ↓
┌─────────────────────────────────────┐
│  Gemini Voice Agent                 │
│  (Answers questions)                │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│  BAML Async Processing Loop         │
│  (Extracts intent & questions)      │
└─────────────────────────────────────┘
    ↓
Call Ends
    ↓
Save Renter Profile (JSON to /profiles/)
```
