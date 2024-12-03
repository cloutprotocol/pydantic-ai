import pytest
from src.config import agent

pytestmark = pytest.mark.anyio

async def test_basic_response(mock_agent):
    response = await agent.run("Hello")
    assert isinstance(response.data, str) 