from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agents.node_agent import CodeAnalysis, ReviewTestFeedback, TestCase


@pytest.fixture
def mock_llm():
    mock = MagicMock()
    mock.ainvoke = AsyncMock(return_value=MagicMock(content="mocked response"))
    with patch("agents.qa_agent.llm", mock):
        yield mock


@pytest.fixture
def mock_analysis_llm():
    mock = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=CodeAnalysis(
            main_functions=["add", "subtract"],
            edge_cases=["negative numbers", "zero values"],
            external_dependencies=[],
        )
    )
    mock.with_structured_output.return_value = mock_structured
    with patch("agents.node_agent.llm", mock):
        yield mock


@pytest.fixture
def mock_pipeline_llm():
    mock = MagicMock()

    analysis_structured = AsyncMock()
    analysis_structured.ainvoke = AsyncMock(
        return_value=CodeAnalysis(
            main_functions=["add"],
            edge_cases=["negative numbers", "zero"],
            external_dependencies=[],
        )
    )
    generate_structured = AsyncMock()
    generate_structured.ainvoke = AsyncMock(
        return_value=[
            TestCase(
                description="test add with positive numbers",
                function_name="test_add",
                test_code="def test_add():\n    assert add(1, 2) == 3\n",
            )
        ]
    )
    review_structured = AsyncMock()
    review_structured.ainvoke = AsyncMock(
        return_value=ReviewTestFeedback(
            issues=[],
            suggestions=[],
            edge_cases_covered=["positive numbers"],
            corrected_test_code="def test_add():\n    assert add(1, 2) == 3\n",
        )
    )

    mock.with_structured_output.side_effect = [
        analysis_structured,
        generate_structured,
        review_structured,
    ]
    with patch("agents.node_agent.llm", mock):
        yield mock


@pytest.fixture
def mock_review_llm():
    mock = MagicMock()
    mock_structured = AsyncMock()
    mock_structured.ainvoke = AsyncMock(
        return_value=ReviewTestFeedback(
            issues=["Missing assertion for zero input"],
            suggestions=["Add test for negative numbers"],
            edge_cases_covered=["positive numbers"],
            corrected_test_code="def test_add():\n    assert add(1, 2) == 3\n",
        )
    )
    mock.with_structured_output.return_value = mock_structured
    with patch("agents.node_agent.llm", mock):
        yield mock
