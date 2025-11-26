# Architecture Documentation

## System Overview

The voice bot is a Modal-based application that integrates Twilio for telephony, Google Gemini for conversational AI, and BAML for intent extraction. The system handles car rental inquiries through voice calls and saves detailed profiles of each interaction.

## Components

### 1. Modal App (`app.py`)
The main application container deployed on Modal's serverless platform.

**Key Features:**
- Serverless deployment with automatic scaling
- Persistent volume for storing renter profiles
- Secure secret management for API keys
- Concurrent request handling (max 100 inputs)

### 2. FastAPI Server
REST API and WebSocket endpoints for handling Twilio interactions.

**Endpoints:**
- `GET /` - Health check endpoint
- `POST /webhook` - Twilio webhook for incoming calls
- `WebSocket /ws/{call_sid}` - Real-time voice communication

### 3. Twilio Integration

**Webhook Flow:**
```
Incoming Call → Twilio → POST /webhook
                              ↓
                         TwiML Response
                              ↓
                    WebSocket Connection URL
```

The webhook receives call metadata (CallSid, From, To) and returns TwiML that:
- Greets the caller
- Establishes WebSocket connection for streaming

### 4. Gemini Voice Agent

**Class: `GeminiVoiceAgent`**

Responsibilities:
- Process user questions about car rentals
- Generate contextual responses
- Maintain conversation history
- Access car detail information

**Features:**
- Model: `gemini-1.5-flash`
- Context-aware responses (last 5 messages)
- Specialized in car rental domain
- Concise, voice-optimized responses

### 5. BAML Processing

**Class: `BAMLProcessor`**

Async functions that run in parallel with the main conversation:

1. **Intent Extraction** (`extract_intent`)
   - Identifies caller's primary intent
   - Examples: pricing inquiry, availability check, reservation

2. **Question Extraction** (`extract_questions`)
   - Captures all distinct questions asked
   - Useful for FAQ analysis

3. **Profile Extraction** (`extract_renter_profile`)
   - Extracts structured information:
     - Name, phone, email
     - Rental dates and location
     - Car preferences
     - Budget range

**BAML Configuration** (`baml_src/main.baml`):
- Defines LLM client (Gemini)
- Declares extraction functions
- Defines data structures (RenterProfile class)

### 6. Call Session Management

**Class: `CallSession`**

Manages state for each active call:

**Attributes:**
- `call_sid`: Unique Twilio call identifier
- `conversation_history`: List of all messages
- `start_time`: Call start timestamp
- `intents`: Extracted intents list
- `questions`: Extracted questions list
- `renter_profile`: Extracted profile data

**Methods:**
- `add_message(role, content)`: Append to conversation
- `get_conversation_text()`: Format as plain text
- `save_profile(profiles_dir)`: Persist to JSON

### 7. Car Detail Database

**Class: `CarDetail`**

Static car rental inventory:

| Type    | Name              | Price/Day | Features                                      |
|---------|-------------------|-----------|-----------------------------------------------|
| Economy | Economy Sedan     | $45       | 4 doors, 5 seats, automatic, AC, Bluetooth    |
| SUV     | Mid-size SUV      | $75       | 5 doors, 7 seats, 4WD, navigation             |
| Luxury  | Luxury Sedan      | $120      | Premium sound, leather seats, sunroof         |
| Van     | Family Van        | $85       | 8 seats, entertainment system                 |

## Data Flow

### Call Lifecycle

```
1. Incoming Call
   ↓
2. Twilio calls /webhook
   ↓
3. Create CallSession
   ↓
4. Return TwiML with WebSocket URL
   ↓
5. WebSocket Connection Established
   ↓
6. Initialize Gemini Agent
   ↓
7. Start BAML Processing Loop (async)
   ↓
8. ┌─────────────────────────────────────┐
   │ Main Loop (until call ends):        │
   │                                     │
   │  User speaks → Audio data →        │
   │  Transcription → Text              │
   │                   ↓                 │
   │  Gemini Agent processes            │
   │                   ↓                 │
   │  Generate response                 │
   │                   ↓                 │
   │  Send audio to caller              │
   │                                     │
   │  Meanwhile (every 5 seconds):      │
   │  - Extract intent                  │
   │  - Extract questions               │
   │  - Update renter profile           │
   └─────────────────────────────────────┘
   ↓
9. Call Ends / WebSocket Disconnect
   ↓
10. Cancel BAML task
   ↓
11. Save renter profile to /profiles/
   ↓
12. Clean up session
```

### BAML Processing Loop

Runs concurrently with main conversation:

```python
while call_active:
    await sleep(5 seconds)
    
    conversation = get_conversation_text()
    
    # Parallel BAML operations
    intent = await extract_intent(conversation)
    questions = await extract_questions(conversation)
    profile = await extract_renter_profile(conversation)
    
    # Update session
    session.intents.append(intent)
    session.questions.extend(questions)
    session.renter_profile.update(profile)
```

## Storage

### Profile JSON Structure

Saved to `/profiles/profile_{call_sid}_{timestamp}.json`:

```json
{
  "call_sid": "CA1234567890",
  "start_time": "2024-01-15T10:30:00",
  "end_time": "2024-01-15T10:35:30",
  "conversation": [
    {
      "role": "user",
      "content": "message text",
      "timestamp": "ISO8601"
    }
  ],
  "intents": ["intent1", "intent2"],
  "questions": ["question1", "question2"],
  "renter_profile": {
    "name": "string",
    "phone": "string",
    "email": "string",
    "rental_dates": "string",
    "car_preferences": ["economy"],
    "budget_range": "string",
    "location": "string",
    "additional_notes": "string"
  }
}
```

## Security

### Secrets Management

Modal Secrets required:
- `gemini-api-key`: Contains `GEMINI_API_KEY`
- `twilio-credentials`: Contains `TWILIO_ACCOUNT_SID` and `TWILIO_AUTH_TOKEN`

### Best Practices

1. Never hardcode API keys
2. Use Modal's Secret.from_name() for secure access
3. Secrets are injected at runtime
4. Not exposed in logs or responses

## Scalability

### Modal Configuration

- **Concurrent inputs**: 100 simultaneous calls
- **Automatic scaling**: Modal handles infrastructure
- **Persistent storage**: Volume for profiles
- **Zero downtime**: Automatic deployment

### Performance Considerations

1. **WebSocket connections**: Each call maintains one connection
2. **BAML processing**: Runs every 5 seconds (adjustable)
3. **Conversation context**: Last 5 messages (memory efficient)
4. **Volume I/O**: Asynchronous profile writing

## Extension Points

### Adding New Car Types

Edit `CarDetail.AVAILABLE_CARS` dictionary in `app.py`

### Custom BAML Functions

Add to `baml_src/main.baml`:
```baml
function CustomExtraction(conversation: string) -> CustomType {
  client Gemini
  prompt #"Your prompt here"#
}
```

### Additional Endpoints

Add to FastAPI `web_app`:
```python
@web_app.get("/custom-endpoint")
async def custom_handler():
    return {"data": "value"}
```

## Monitoring

### Logs

View Modal logs:
```bash
modal app logs voice-bot-gemini-baml
```

### Metrics to Track

- Call duration
- Intent distribution
- Common questions
- Profile completeness
- Error rates

## Testing

Run tests:
```bash
pytest tests/test_app.py -v
```

Test coverage:
- Health check endpoint ✓
- Car detail retrieval ✓
- Call session management ✓
- BAML processor functions ✓
- Twilio webhook handler ✓
- Profile saving ✓

## Troubleshooting

### Common Issues

1. **WebSocket connection fails**
   - Check Modal deployment URL
   - Verify Twilio webhook configuration
   - Review Modal logs for errors

2. **Gemini API errors**
   - Verify API key in Modal secrets
   - Check API quota limits
   - Review error messages in logs

3. **BAML extraction not working**
   - Ensure conversation has sufficient content
   - Check BAML configuration
   - Verify Gemini API access

4. **Profiles not saving**
   - Check Modal volume permissions
   - Verify /profiles directory exists
   - Review async save errors in logs
