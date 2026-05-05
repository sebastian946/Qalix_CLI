import pytest

from agents.node_agent import AgentState, graph


def _initial_state() -> AgentState:
    return {
        "code": "def add(a, b): return a + b",
        "filename": "math.py",
        "status": "pending",
        "is_finished": False,
    }


@pytest.mark.asyncio
async def test_graph_passes_through_all_three_nodes_in_order(mock_pipeline_llm) -> None:
    await graph.ainvoke(_initial_state())

    calls = mock_pipeline_llm.with_structured_output.call_args_list
    assert len(calls) == 3
    from agents.node_agent import CodeAnalysis, ReviewTestFeedback
    assert calls[0][0][0] is CodeAnalysis
    assert calls[2][0][0] is ReviewTestFeedback


@pytest.mark.asyncio
async def test_graph_final_state_has_all_fields_populated(mock_pipeline_llm) -> None:
    result = await graph.ainvoke(_initial_state())

    assert "analysis" in result
    assert "test_cases" in result
    assert "final_tests" in result
    assert isinstance(result["analysis"], dict)
    assert isinstance(result["test_cases"], list)
    assert isinstance(result["final_tests"], str)


@pytest.mark.asyncio
async def test_graph_calls_llm_exactly_three_times(mock_pipeline_llm) -> None:
    await graph.ainvoke(_initial_state())

    assert mock_pipeline_llm.with_structured_output.call_count == 3


@pytest.mark.asyncio
async def test_graph_completes_without_error_with_valid_python(mock_pipeline_llm) -> None:
    result = await graph.ainvoke(_initial_state())

    assert result is not None
    assert "final_tests" in result
    assert len(result["final_tests"]) > 0
    assert "def test_" in result["final_tests"]
