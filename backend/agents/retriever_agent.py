from utils.llm import chat

RETRIEVER_PROMPT = """
You are a Retrieval Agent.

Your only responsibility is retrieving factual information.

Do NOT analyze.

Do NOT compare.

Return concise factual information only.
"""


async def retrieve(task: str):

    result = await chat(
        RETRIEVER_PROMPT,
        task
    )

    return result