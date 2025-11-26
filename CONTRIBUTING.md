# Contributing Guide

Thank you for your interest in contributing to the voice-bot-gemini-baml project!

## Development Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/Ben-Epstein/voice-bot-gemini-baml.git
   cd voice-bot-gemini-baml
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

## Code Style

- Follow PEP 8 guidelines
- Use type hints where possible
- Write docstrings for classes and functions
- Keep functions focused and single-purpose

## Testing

### Running Tests

```bash
pytest tests/test_app.py -v
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Use descriptive test function names
- Test one thing per test function
- Use fixtures for common setup

Example:
```python
def test_new_feature():
    """Test description of what it validates"""
    # Arrange
    session = CallSession("test_123")
    
    # Act
    result = session.some_method()
    
    # Assert
    assert result == expected_value
```

## Making Changes

### Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update documentation

3. **Test your changes**
   ```bash
   pytest tests/ -v
   python -m py_compile app.py
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/your-feature-name
   ```

## Areas for Contribution

### High Priority

1. **Audio Processing**
   - Implement actual audio transcription from Twilio streams
   - Add text-to-speech for responses
   - Handle audio format conversions

2. **BAML Integration**
   - Generate actual BAML client code
   - Replace simulated BAML functions with real ones
   - Add more extraction functions

3. **Conversation Features**
   - Add support for multiple languages
   - Implement conversation interruption handling
   - Add sentiment analysis

### Medium Priority

4. **Database Integration**
   - Replace file-based storage with database
   - Add profile search and analytics
   - Implement reservation system

5. **Enhanced Car Details**
   - Add real-time availability checking
   - Integrate with actual inventory systems
   - Add pricing rules (weekends, seasons, etc.)

6. **Testing & Monitoring**
   - Add integration tests
   - Implement conversation quality metrics
   - Add performance monitoring

### Low Priority

7. **UI Dashboard**
   - Build admin dashboard for viewing calls
   - Add analytics visualizations
   - Profile management interface

8. **Documentation**
   - Add API documentation
   - Create video tutorials
   - Write blog posts about implementation

## Code Review Process

1. All changes require a pull request
2. Tests must pass
3. Code should be documented
4. At least one approval required
5. Address review comments

## Project Structure

```
voice-bot-gemini-baml/
├── app.py                 # Main application
├── baml_src/             # BAML function definitions
│   └── main.baml
├── tests/                # Test files
│   ├── __init__.py
│   └── test_app.py
├── requirements.txt      # Python dependencies
├── pyproject.toml        # Project configuration
├── modal.toml           # Modal configuration
├── README.md            # Project overview
├── SETUP.md            # Setup instructions
├── ARCHITECTURE.md     # Architecture documentation
├── QUICK_START.md      # Quick start guide
└── CONTRIBUTING.md     # This file
```

## Adding New Features

### Example: Adding a New BAML Function

1. **Define in BAML** (`baml_src/main.baml`)
   ```baml
   function ExtractSentiment(conversation: string) -> string {
     client Gemini
     prompt #"Analyze sentiment of this conversation: {{ conversation }}"#
   }
   ```

2. **Add to BAMLProcessor** (`app.py`)
   ```python
   async def extract_sentiment(self, conversation: str) -> str:
       # Implementation here
       pass
   ```

3. **Use in WebSocket handler**
   ```python
   sentiment = await baml_processor.extract_sentiment(conversation_text)
   session.sentiment = sentiment
   ```

4. **Add tests** (`tests/test_app.py`)
   ```python
   @pytest.mark.asyncio
   async def test_sentiment_extraction():
       processor = BAMLProcessor()
       result = await processor.extract_sentiment("Happy conversation")
       assert result in ["positive", "negative", "neutral"]
   ```

### Example: Adding a New Endpoint

1. **Define route** (`app.py`)
   ```python
   @web_app.get("/stats")
   async def get_stats():
       return {"total_calls": len(active_sessions)}
   ```

2. **Add test**
   ```python
   def test_stats_endpoint(client):
       response = client.get("/stats")
       assert response.status_code == 200
   ```

## Common Issues

### Import Errors
- Ensure virtual environment is activated
- Install all dependencies: `pip install -r requirements.txt`

### Modal Deployment Fails
- Check Modal authentication: `modal token new`
- Verify secrets exist: `modal secret list`

### Tests Failing
- Check test isolation (use fixtures)
- Verify test data is not persisted
- Use `tmp_path` for file operations

## Getting Help

- Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
- Review [SETUP.md](SETUP.md) for configuration
- Open an issue for bugs or questions
- Start a discussion for feature ideas

## License

By contributing, you agree that your contributions will be licensed under the same license as the project (see LICENSE file).

## Questions?

Feel free to open an issue or reach out to the maintainers!
