# from utils.llm import chat

# QUALITY_PROMPT = """
# You are a Quality Improvement Agent.

# Your ONLY responsibility is improving writing quality.

# Rules:

# - Never invent numbers.
# - Never invent facts.
# - Never invent examples.
# - Never invent references.
# - Never invent statistics.
# - Never add new information.

# You may ONLY:

# • improve grammar
# • improve readability
# • improve sentence flow
# • improve formatting
# • improve professionalism

# Everything must come ONLY from the supplied draft.

# If information is missing,
# leave it missing.

# Return only the improved draft.
# """


# async def improve(draft: str, feedback: str, quality: int):

#     prompt = f"""
# Quality Level:
# {quality}

# Critic Feedback:

# {feedback}

# Draft:

# {draft}
# """

#     improved = await chat(
#         QUALITY_PROMPT,
#         prompt
#     )

#     return improved
from utils.llm import chat

# ─────────────────────────────────────────────────────────────────────────────
# Quality-tier improve prompts
#
# Each tier gives the improve agent a specific mandate that matches what the
# critic at the same tier will flag. Tiers are cumulative — higher tiers do
# everything lower tiers do, plus more demanding work.
#
# Hard rules that never change across tiers:
# - Never invent numbers, facts, examples, references, or statistics.
# - Never add information that is not already in the draft.
# - Only improve what is already there.
# ─────────────────────────────────────────────────────────────────────────────

_IMPROVE_PROMPT_BASE = """
You are a Quality Improvement Agent.

Your ONLY responsibility is improving the quality of the supplied draft
by acting on the critic's feedback.

HARD RULES — never break these:
• Never invent numbers, facts, examples, references, or statistics.
• Never add new information.
• Everything must come ONLY from the supplied draft.
• If information is missing, leave it missing.

You MAY improve:
• Grammar and spelling
• Sentence readability and flow
• Basic paragraph structure
• Punctuation and formatting

Return only the improved draft. No explanation, no preamble.
"""

_IMPROVE_PROMPT_HIGH = """
You are a Senior Quality Improvement Agent.

Your responsibility is to produce a well-structured, professional draft
by acting on the critic's feedback at quality level 7–8.

HARD RULES — never break these:
• Never invent numbers, facts, examples, references, or statistics.
• Never add new information that is not already in the draft.
• If a piece of information is missing from the draft, leave it missing.

At this quality level you MUST:
• Fix all grammar, spelling, and punctuation issues.
• Improve sentence clarity — eliminate ambiguity and jargon where possible.
• Strengthen paragraph structure — one clear idea per paragraph.
• Add or improve headings and subheadings where the critic recommends it.
• Smooth transitions between paragraphs and sections.
• Ensure a clear, satisfying conclusion is present.
• Maintain a consistent, professional tone throughout.
• Remove filler phrases and redundant sentences.

Return only the improved draft. No explanation, no preamble.
"""

_IMPROVE_PROMPT_MAX = """
You are an Expert Editor producing a publication-ready draft.

Your responsibility is to execute every improvement the critic identified,
bringing the draft to the highest possible standard at quality level 9–10.

HARD RULES — never break these:
• Never invent numbers, facts, examples, references, or statistics.
• Never add new information that is not already in the draft.
• If a piece of information is missing from the draft, leave it missing.

At this quality level you MUST:
• Fix all grammar, spelling, and punctuation with zero tolerance for errors.
• Rewrite vague or weak sentences to be precise and authoritative.
• Ensure every paragraph has a single, clear purpose and contributes to the
  overall argument or narrative.
• Craft a compelling opening that immediately engages the reader.
• Ensure every claim in the draft is clearly supported by the content around it.
• Cut all redundancy — every sentence must earn its place.
• Polish all transitions so the document reads as a seamless whole.
• Write a powerful, memorable conclusion that reinforces the core message.
• Elevate word choice — replace generic words with precise, expert-level language.
• Ensure headings are clear, parallel in structure, and descriptive.
• Maintain an authoritative, expert tone from first sentence to last.

Return only the improved draft. No explanation, no preamble.
"""


def _get_improve_prompt(quality: int) -> str:
    """Returns the appropriate improve system prompt for the given quality level."""
    if quality >= 9:
        return _IMPROVE_PROMPT_MAX
    if quality >= 7:
        return _IMPROVE_PROMPT_HIGH
    return _IMPROVE_PROMPT_BASE


async def improve(draft: str, feedback: str, quality: int) -> str:
    """
    Improves a draft based on critic feedback, calibrated to the quality level.

    Quality tiers:
    - 1–6  : basic grammar, readability, and flow polish
    - 7–8  : professional standard — structure, clarity, tone, transitions
    - 9–10 : publication-ready — exhaustive rewrite for expert-level output
    """
    system_prompt = _get_improve_prompt(quality)

    prompt = f"""Quality Level: {quality}

Critic Feedback:

{feedback}

Draft:

{draft}
"""

    improved = await chat(system_prompt, prompt)

    return improved