import pytest
from pydantic_ai.models.test import TestModel
from src.config import agent

@pytest.fixture
def mock_agent():
    with agent.override(model=TestModel()):
        yield 