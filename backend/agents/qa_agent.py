from core.config import llm

_SYSTEM_PROMPT = (
    "You are a QA expert and you generate unit tests using the language "
    "and create pipelines for CD/CI"
)


async def chat(code: str, filename: str) -> str:
    messages = [
        ("system", _SYSTEM_PROMPT),
        ("user", f"Generate a unit test for the following code:\n\n```{filename}\n{code}\n```"),
    ]
    response = await llm.ainvoke(messages)
    return str(response.content)
