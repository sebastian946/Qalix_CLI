import pytest

from agents.node_agent import AgentState, analysis_node, review_test_node


def _make_state(**overrides) -> AgentState:
    base: AgentState = {
        "code": "def add(a, b): return a + b",
        "filename": "math.py",
        "analysis": {},
        "status": "pending",
        "is_finished": False,
    }
    base.update(overrides)
    return base


@pytest.mark.asyncio
async def test_analysis_node_returns_analysis_field(mock_analysis_llm) -> None:
    result = await analysis_node(_make_state())

    assert "analysis" in result
    analysis = result["analysis"]
    assert "main_functions" in analysis
    assert "edge_cases" in analysis
    assert "external_dependencies" in analysis


@pytest.mark.asyncio
async def test_analysis_node_includes_code_in_prompt(mock_analysis_llm) -> None:
    state = _make_state(code="def multiply(a, b): return a * b", filename="math.py")
    await analysis_node(state)

    mock_structured = mock_analysis_llm.with_structured_output.return_value
    call_messages = mock_structured.ainvoke.call_args[0][0]
    user_message = next(msg[1] for msg in call_messages if msg[0] == "user")
    assert "def multiply(a, b): return a * b" in user_message
    assert "math.py" in user_message


@pytest.mark.asyncio
async def test_analysis_node_does_not_modify_other_fields(mock_analysis_llm) -> None:
    state = _make_state(status="pending", is_finished=False)
    result = await analysis_node(state)

    assert "status" not in result
    assert "is_finished" not in result
    assert "code" not in result
    assert "filename" not in result


@pytest.mark.asyncio
async def test_analysis_node_handles_empty_code(mock_analysis_llm) -> None:
    state = _make_state(code="", filename="empty.py")
    result = await analysis_node(state)

    assert "analysis" in result
    assert isinstance(result["analysis"], dict)


# --- review_test_node ---

_SAMPLE_TEST_CASES = [
    {"description": "test add", "function_name": "test_add", "test_code": "assert add(1, 2) == 3"},
]


@pytest.mark.asyncio
async def test_review_node_output_saved_in_final_tests(mock_review_llm) -> None:
    state = _make_state(test_cases=_SAMPLE_TEST_CASES)
    result = await review_test_node(state)

    assert "final_tests" in result
    assert isinstance(result["final_tests"], str)
    assert len(result["final_tests"]) > 0


@pytest.mark.asyncio
async def test_review_node_includes_tests_in_prompt(mock_review_llm) -> None:
    test_cases = [{"description": "test multiply", "function_name": "test_multiply", "test_code": "assert multiply(2, 3) == 6"}]
    state = _make_state(test_cases=test_cases)
    await review_test_node(state)

    mock_structured = mock_review_llm.with_structured_output.return_value
    call_messages = mock_structured.ainvoke.call_args[0][0]
    user_message = next(msg[1] for msg in call_messages if msg[0] == "user")
    assert "test_multiply" in user_message


@pytest.mark.asyncio
async def test_review_node_result_has_pytest_syntax(mock_review_llm) -> None:
    state = _make_state(test_cases=_SAMPLE_TEST_CASES)
    result = await review_test_node(state)

    assert "def test_" in result["final_tests"]
