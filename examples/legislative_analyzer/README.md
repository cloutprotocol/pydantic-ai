# Legislative Bill Analyzer

This example demonstrates how to use PydanticAI to create a powerful legislative bill analysis tool. It showcases several advanced features of PydanticAI:

- Structured data modeling with Pydantic
- Dependency injection for external services
- Smart caching of LLM responses
- Semantic search capabilities

## Features

- Bill section analysis and summarization
- Semantic search across bill contents
- Impact analysis by sector
- Funding allocation tracking
- Amendment tracking
- Citation management

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up your environment variables:
```bash
cp .env.example .env
# Add your OpenAI API key to .env
```

3. Run the example:
```bash
python main.py
```

## Project Structure

```
legislative_analyzer/
├── models/
│   ├── __init__.py
│   ├── bill.py         # Bill-related data models
│   ├── analysis.py     # Analysis result models
│   └── search.py       # Search-related models
├── services/
│   ├── __init__.py
│   ├── analyzer.py     # Core analysis logic
│   ├── loader.py       # Bill text loading
│   └── search.py       # Search implementation
├── utils/
│   ├── __init__.py
│   └── text.py         # Text processing utilities
├── main.py             # Example usage
├── requirements.txt
└── README.md
```

## Usage Examples

```python
from legislative_analyzer.services.analyzer import analyze_bill
from legislative_analyzer.services.search import search_bill_contents

# Analyze a bill
analysis = await analyze_bill(
    bill_url="https://www.congress.gov/bill/117th-congress/house-bill/5376/text",
    focus_areas=["climate", "healthcare"]
)

# Search for specific provisions
results = await search_bill_contents(
    analysis=analysis,
    query="What are the clean energy tax credits?"
)
```

## Example Outputs

See the `examples/` directory for sample outputs and use cases.