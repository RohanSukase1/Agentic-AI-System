from utils.llm import chat, stream_chat

WRITER_PROMPT = """
You are a Professional Writing Agent.

Responsibilities:
- Write polished, professional content.
- Use the supplied analysis.
- Never invent facts.
- Never invent statistics.
- Never invent references.
- Never introduce information that was not provided.
- Produce clear, well-structured writing.
"""


# ---------------------------------------------------------
# Normal Writing (Existing Behaviour)
# ---------------------------------------------------------

async def write(task: str, context: dict):

    analysis = []

    for value in context.values():

        if value["agent"] == "analyzer":
            analysis.append(value["output"])

    prompt = f"""
Task:

{task}

Analysis:

{chr(10).join(analysis)}
"""

    result = await chat(
        WRITER_PROMPT,
        prompt
    )

    return result


# ---------------------------------------------------------
# Streaming Writer
# ---------------------------------------------------------

async def stream_write(task: str, context: dict):

    analysis = []

    for value in context.values():

        if value["agent"] == "analyzer":
            analysis.append(value["output"])

    prompt = f"""
Task:

{task}

Analysis:

{chr(10).join(analysis)}
"""

    full_response = ""

    async for token in stream_chat(
        WRITER_PROMPT,
        prompt
    ):

        full_response += token

        yield {
            "type": "token",
            "content": token
        }

    yield {
        "type": "writer_complete",
        "content": full_response
    }