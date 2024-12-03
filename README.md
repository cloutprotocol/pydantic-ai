# PydanticAI Examples

This repository contains practical examples of using PydanticAI for building LLM-powered applications. PydanticAI is a powerful framework that combines Pydantic's type safety with LLM capabilities.

## Setup

1. Clone this repository:
```bash
git clone https://github.com/cloutprotocol/pydantic-ai.git
cd pydantic-ai
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up your environment variables:
```bash
cp .env.example .env
# Edit .env with your OpenAI API key
```

## Examples

1. **Recipe Generator**: Demonstrates using PydanticAI for structured recipe generation
2. **Customer Support Agent**: Shows how to build a support agent with structured responses
3. **Data Analyzer**: Example of using PydanticAI for structured data analysis

Each example is self-contained in its own directory under `examples/`.

## Running the Examples

Each example can be run directly:

```bash
python examples/recipe_generator.py
python examples/customer_support.py
python examples/data_analyzer.py
```

## Key Features Demonstrated

1. **Type Safety**: All examples use Pydantic models for type-safe inputs and outputs
2. **Structured Outputs**: Show how to get structured, predictable responses from LLMs
3. **Error Handling**: Examples include proper error handling and validation
4. **Real-world Use Cases**: Practical applications that can be adapted for production use

## Documentation

For more information about PydanticAI, visit the [official documentation](https://ai.pydantic.dev).