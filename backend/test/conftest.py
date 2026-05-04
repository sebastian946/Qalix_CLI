from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="mocked response"))
    with patch("agents.qa_agent.llm", mock):
        yield mock
