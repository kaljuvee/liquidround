# Local Testing Guide for LiquidRound

## Quick Start

1. **Clone the repository:**
```bash
git clone https://github.com/kaljuvee/liquidround.git
cd liquidround
```

2. **Install dependencies (no version constraints):**
```bash
pip install -r requirements.txt
```

3. **Environment is already configured** with API keys in `.env` file:
   - ✅ OpenAI API Key
   - ✅ Polygon.io API Key  
   - ✅ Exa.ai API Key

4. **Run the application:**
```bash
streamlit run Home.py
```

5. **Access the application:**
   - Open your browser to `http://localhost:8501`
   - The application will start with the LiquidRound interface

## Testing

Run the full test suite:
```bash
pytest tests/ -v
```

Expected output: **10 tests passed**

## Project Structure

```
liquidround/
├── Home.py                 # Main entry point
├── agents/                # Core application
│   ├── Home.py            # Streamlit app
│   ├── workflow.py        # LangGraph workflow
│   └── [agent files]     # Individual agents
├── prompts/               # Agent prompts (.md format)
├── utils/                 # Utility modules
├── tests/                 # Test suite
└── .env                   # API credentials (included)
```

## Sample Queries to Test

### Buyer-Led M&A:
- "Find fintech acquisition targets with $10-50M revenue"
- "Looking to acquire a SaaS company in healthcare"

### Seller-Led M&A:
- "Preparing to sell our B2B software company"
- "Need help finding buyers for our logistics business"

### IPO:
- "Assessing IPO readiness for our tech company"
- "Planning to go public in the next 18 months"

## Troubleshooting

If you encounter import errors:
1. Ensure you're in the project root directory
2. Check that all dependencies are installed: `pip list`
3. Verify Python version: `python --version` (3.8+ required)

## API Keys Included

The following API keys are pre-configured in `.env`:
- **OpenAI**: For LLM interactions
- **Polygon.io**: For financial data
- **Exa.ai**: For enhanced search capabilities

All keys are valid and ready for testing.
