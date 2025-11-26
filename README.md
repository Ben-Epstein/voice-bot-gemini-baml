# voice-bot-gemini-baml

A voice bot using Twilio, Gemini, and BAML for car rental information.

## Features

- **Twilio Integration**: Receives incoming phone calls via webhook
- **Gemini Voice Agent**: Answers questions about car rental details
- **BAML Intent Extraction**: Asynchronously extracts caller intent and questions
- **Profile Saving**: Saves renter profiles as JSON after each call

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Deploy to Modal:
```bash
modal deploy app.py
```

## Architecture

The application consists of:

1. **Webhook Route** (`/webhook`): Receives incoming calls from Twilio
2. **WebSocket Route** (`/ws/{call_sid}`): Handles real-time voice communication
3. **Gemini Agent**: Processes voice input and provides responses about car rentals
4. **BAML Functions**: Extracts intent and questions asynchronously
5. **Profile Storage**: Saves renter profiles to `profiles/` directory

## Usage

Configure your Twilio phone number to point to the webhook URL provided by Modal after deployment.
