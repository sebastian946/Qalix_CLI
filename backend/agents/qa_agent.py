import time

import structlog

from core.config import llm

logger = structlog.get_logger()

# claude-haiku-4-5 pricing (USD per million tokens)
_INPUT_COST_PER_1M = 0.80
_OUTPUT_COST_PER_1M = 4.00

_SYSTEM_PROMPT = (
    "You are a QA expert and you generate unit tests using the language "
    "and create pipelines for CD/CI"
)


async def chat(code: str, filename: str) -> str:
    messages = [
        ("system", _SYSTEM_PROMPT),
        ("user", f"Generate a unit test for the following code:\n\n```{filename}\n{code}\n```"),
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
        tokens_input=input_tokens,
        tokens_output=output_tokens,
        tokens_total=input_tokens + output_tokens,
        duration_ms=duration_ms,
        cost_usd=cost_usd,
    )

    return str(response.content)
