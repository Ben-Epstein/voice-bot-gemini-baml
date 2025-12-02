# voice-bot-gemini-baml

A voice bot using Twilio, Gemini, and BAML for car rental information.

## Features

- **Twilio Integration**: Receives incoming phone calls via webhook
- **Gemini Voice Agent**: Answers questions about car rental details
- **BAML Intent Extraction**: Asynchronously extracts caller intent and questions (currently simulated - see BAML Integration section)
- **Profile Saving**: Saves renter profiles as JSON after each call

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Deploy to Modal:
```bash
uv run modal deploy --env NE_LECTURE src/app.py      
```

Or run locally (set `RUN_LOCAL=1`)
```bash
uv run uvicorn --app-dir src app:web_app --host 0.0.0.0 --port 8000
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

## BAML Integration

The current implementation includes BAML function definitions in `baml_src/main.baml` and a simulated processor for demonstration. To enable full BAML integration:

1. **Generate BAML client code:**
   ```bash
   uv run baml-cli generate
   ```

2. **Update the BAMLProcessor class** in `app.py` to use the generated client (see inline comments in the code)

3. **Replace simulated methods** with actual BAML function calls

The BAML definitions include:
- `ExtractIntent`: Identifies caller's primary intent
- `ExtractQuestions`: Captures distinct questions asked
- `ExtractRenterProfile`: Extracts structured profile information

For more details, see [ARCHITECTURE.md](ARCHITECTURE.md) and [CONTRIBUTING.md](CONTRIBUTING.md).
