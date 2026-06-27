from utils.llm import chat

CRITIC_PROMPT = """
You are a Critic Agent.

Your ONLY job is to review a draft.

DO NOT rewrite it.

Evaluate:

Strengths

- Well structured
- Clear headings
- Logical flow

Weaknesses

- Long paragraphs
- Missing conclusion
- Grammar issues

Recommendations

- Split paragraph 2
- Improve transition
- Strengthen conclusion

Return concise improvement suggestions.


Do not rewrite the content.
"""


async def critic(draft: str):

    feedback = await chat(
        CRITIC_PROMPT,
        draft
    )

    return feedback