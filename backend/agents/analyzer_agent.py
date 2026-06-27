from utils.llm import chat

ANALYZER_PROMPT = """
You are an Analysis Agent.

You receive retrieved information.

Your job is to:

- compare
- summarize
- extract insights

Do NOT write blogs.

Do NOT write LinkedIn posts.
"""


async def analyze(task: str, context: dict):

    retrieval_results = []

    for value in context.values():

        if value["agent"] == "retriever":
            retrieval_results.append(value["output"])

    prompt = f"""

Task:

{task}

Retrieved Information:

{chr(10).join(retrieval_results)}

"""

    result = await chat(
        ANALYZER_PROMPT,
        prompt
    )

    return result