import pytest

from agents.qa_agent import chat


@pytest.mark.asyncio
async def test_chat_returns_llm_response(mock_llm) -> None:
    result = await chat(code="def add(a, b): return a + b", filename="math.py")

    assert result == "mocked response"
    mock_llm.ainvoke.assert_called_once()


@pytest.mark.asyncio
async def test_chat_includes_code_and_filename_in_prompt(mock_llm) -> None:
    await chat(code="def greet(): pass", filename="greet.py")

    call_args = mock_llm.ainvoke.call_args[0][0]
    last_message = call_args[-1][1]
    assert "def greet(): pass" in last_message
    assert "greet.py" in last_message
