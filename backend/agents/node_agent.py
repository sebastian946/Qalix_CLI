from typing import NotRequired, TypedDict, cast

from pydantic import BaseModel

from core.config import llm

_SYSTEM_PROMPT_ANALYSIS = (
    "You are a QA expert. Analyze the provided code and identify: "
    "the main functions that should be tested, edge cases to cover, "
    "and external dependencies that need to be mocked."
)

_SYSTEM_PROMPT_GENERATE_TEST = (
    "You are a QA expert. Generate unit test cases for the provided code based on the analysis. "
    "The unit test should be written in the same language as the provided code and should cover "
    "the main functions and edge cases identified in the analysis."
)

_SYSTEM_PROMPT_REVIEW_TEST = (
    "You are a QA expert. Review the generated unit tests and provide feedback on their quality, "
    "coverage, and any potential improvements. Focus on whether the tests effectively cover the main functions and edge cases. "
    "Detect wrong assertions, missing edge cases, incorrectly configured mocks, and any issues with the test code itself. "
    "Return the fully corrected test code with all issues fixed, using pytest syntax."
)

class AgentState(TypedDict):
    code: str
    filename: str
    status: str
    is_finished: bool
    analysis: NotRequired[dict]
    test_cases: NotRequired[list[dict]]
    final_tests: NotRequired[str]


class CodeAnalysis(BaseModel):
    main_functions: list[str]
    edge_cases: list[str]
    external_dependencies: list[str]

class TestCase(BaseModel):
    description: str
    function_name: str
    test_code: str

class ReviewTestFeedback(BaseModel):
    issues: list[str]
    suggestions: list[str]
    edge_cases_covered: list[str]
    corrected_test_code: str


async def analysis_node(state: AgentState) -> dict:
    structured_llm = llm.with_structured_output(CodeAnalysis)
    messages = [
        ("system", _SYSTEM_PROMPT_ANALYSIS),
        ("user", f"Analyze this code:\n\n```{state['filename']}\n{state['code']}\n```"),
    ]
    result = cast(CodeAnalysis, await structured_llm.ainvoke(messages))
    return {"analysis": result.model_dump()}

async def generate_test_node(state: AgentState) -> dict:
    structured_llm = llm.with_structured_output(list[TestCase])
    analysis = state.get("analysis", {})
    messages = [
        ("system", _SYSTEM_PROMPT_GENERATE_TEST),
        ("user", f"Based on the following analysis, generate unit tests:\n\n{analysis}"),
    ]
    result = cast(list[TestCase], await structured_llm.ainvoke(messages))
    return {"test_cases": [test_case.model_dump() for test_case in result]}

async def review_test_node(state: AgentState) -> dict:
    structured_llm = llm.with_structured_output(ReviewTestFeedback)
    test_cases = state.get("test_cases", [])
    messages = [
        ("system", _SYSTEM_PROMPT_REVIEW_TEST),
        ("user", f"Review the following unit tests and provide feedback:\n\n{test_cases}"),
    ]
    result = cast(ReviewTestFeedback, await structured_llm.ainvoke(messages))
    return {"final_tests": result.corrected_test_code}