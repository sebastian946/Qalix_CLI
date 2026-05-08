import os
import time

import structlog

from core.config import llm

logger = structlog.get_logger()

# claude-haiku-4-5 pricing (USD per million tokens)
_INPUT_COST_PER_1M = 0.80
_OUTPUT_COST_PER_1M = 4.00

# Maps file extension → (language name, test framework)
_EXTENSION_MAP: dict[str, tuple[str, str]] = {
    ".py":    ("Python",     "pytest"),
    ".js":    ("JavaScript", "Jest"),
    ".ts":    ("TypeScript", "Jest with ts-jest"),
    ".go":    ("Go",         "the Go standard testing package (go test)"),
    ".java":  ("Java",       "JUnit 5"),
    ".rb":    ("Ruby",       "RSpec"),
    ".php":   ("PHP",        "PHPUnit"),
    ".cs":    ("C#",         "xUnit"),
    ".cpp":   ("C++",        "Google Test (gtest)"),
    ".rs":    ("Rust",       "the built-in Rust testing framework (cargo test)"),
    ".kt":    ("Kotlin",     "JUnit 5 with Kotlin"),
    ".swift": ("Swift",      "XCTest"),
}


def _build_system_prompt(language: str, framework: str) -> str:
    return (
        f"You are a QA expert specializing in {language}. "
        f"Generate comprehensive unit tests using {framework}. "
        f"Cover happy paths, edge cases, and error scenarios. "
        f"Output only the test code, ready to use in a CD/CI pipeline."
    )


async def chat(code: str, filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    language, framework = _EXTENSION_MAP.get(ext, ("the detected programming language", "the standard testing framework"))
    system_prompt = _build_system_prompt(language, framework)

    messages = [
        ("system", system_prompt),
        ("user", f"Generate unit tests for the following {language} code:\n\n```{filename}\n{code}\n```"),
    ]

    start_time = time.perf_counter()
    response = await llm.ainvoke(messages)
    duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

    usage = getattr(response, "usage_metadata", None) or {}
    input_tokens: int = usage.get("input_tokens", 0)
    output_tokens: int = usage.get("output_tokens", 0)
    cost_usd = round(
        (input_tokens * _INPUT_COST_PER_1M + output_tokens * _OUTPUT_COST_PER_1M) / 1_000_000,
        6,
    )

    logger.info(
        "agent_execution_completed",
        filename=filename,
        language=language,
        framework=framework,
        tokens_input=input_tokens,
        tokens_output=output_tokens,
        tokens_total=input_tokens + output_tokens,
        duration_ms=duration_ms,
        cost_usd=cost_usd,
    )

    return str(response.content)
