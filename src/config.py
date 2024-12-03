import os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai import models

load_dotenv()

# Prevent accidental API calls during testing
models.ALLOW_MODEL_REQUESTS = False 

agent = Agent(
    f"openai:{os.getenv('MODEL_NAME', 'gpt-4')}",
    system_prompt=os.getenv('SYSTEM_PROMPT', "You are a helpful AI assistant.")
) 