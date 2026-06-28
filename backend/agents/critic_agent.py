# from utils.llm import chat

# CRITIC_PROMPT = """
# You are a Critic Agent.

# Your ONLY job is to review a draft.

# DO NOT rewrite it.

# Evaluate:

# Strengths

# - Well structured
# - Clear headings
# - Logical flow

# Weaknesses

# - Long paragraphs
# - Missing conclusion
# - Grammar issues

# Recommendations

# - Split paragraph 2
# - Improve transition
# - Strengthen conclusion

# Return concise improvement suggestions.


# Do not rewrite the content.
# """


# async def critic(draft: str):

#     feedback = await chat(
#         CRITIC_PROMPT,
#         draft
#     )

#     return feedback
from utils.llm import chat

# ─────────────────────────────────────────────────────────────────────────────
# Quality-tier critic prompts
#
# Each tier tells the critic which dimensions to focus on so its feedback
# matches what the improve agent actually needs to do at that quality level.
# The tiers are intentionally specific — a vague "improve it" note produces
# a vague rewrite; concrete, targeted notes produce concrete improvements.
# ─────────────────────────────────────────────────────────────────────────────

_CRITIC_PROMPT_BASE = """
You are a Critic Agent.

Your ONLY job is to review a draft and return structured improvement notes.

DO NOT rewrite the draft.
DO NOT invent facts, examples, or statistics.
DO NOT add information that is not already in the draft.

Your review must be concise, specific, and actionable.

Format your response as three labelled sections:

STRENGTHS
- List what works well (be brief)

WEAKNESSES
- List specific problems (be precise: name the paragraph, section, or sentence)

RECOMMENDATIONS
- List concrete, numbered improvement actions the writer can act on directly

Return only the review. No preamble, no sign-off.
"""

_CRITIC_PROMPT_HIGH = """
You are a Senior Critic Agent reviewing a high-quality draft (quality level 7–8).

Your ONLY job is to return structured improvement notes. DO NOT rewrite the draft.

At this quality level you must evaluate:

1. Structure — Are headings clear? Does the document flow logically section to section?
2. Completeness — Are all key points covered with sufficient supporting detail?
3. Clarity — Are sentences easy to parse? Are there any ambiguous or vague statements?
4. Professionalism — Is the tone consistent and appropriate throughout?
5. Transitions — Do paragraphs and sections connect smoothly?
6. Conclusion — Is there a clear, satisfying closing statement?

Format your response as three labelled sections:

STRENGTHS
- What works well at a professional level

WEAKNESSES
- Specific structural, clarity, completeness, or tone issues (name the exact location)

RECOMMENDATIONS
- Numbered, actionable improvements (e.g. "Split paragraph 3 into two paragraphs",
  "Add a one-sentence transition between the Analysis and Conclusion sections")

DO NOT invent facts. DO NOT rewrite content. Return only the review.
"""

_CRITIC_PROMPT_MAX = """
You are an Expert Editor reviewing a publication-ready draft (quality level 9–10).

Your ONLY job is to return exhaustive, precise improvement notes. DO NOT rewrite the draft.

At this quality level you must evaluate every dimension:

1. Opening impact — Does the introduction immediately engage the reader?
2. Argument / narrative structure — Is there a clear through-line from start to finish?
3. Depth — Are claims supported with specifics (data, examples, comparisons)?
4. Precision of language — Are any words vague, redundant, or imprecise?
5. Expert tone — Does the writing demonstrate subject-matter authority?
6. Paragraph-level coherence — Does every paragraph serve a single clear purpose?
7. Transitions — Are all section and paragraph transitions seamless?
8. Closing strength — Does the conclusion reinforce the core message memorably?
9. Redundancy — Is there any repeated content that should be cut?
10. Factual grounding — Are all claims traceable to the provided research?

Format your response as three labelled sections:

STRENGTHS
- Specific strengths at publication level

WEAKNESSES
- Precise, located issues (e.g. "Paragraph 2, sentence 3: vague claim with no supporting detail")

RECOMMENDATIONS
- Numbered, surgical improvement actions ordered by impact

DO NOT invent facts. DO NOT rewrite content. Return only the review.
"""


def _get_critic_prompt(quality: int) -> str:
    """Returns the appropriate critic system prompt for the given quality level."""
    if quality >= 9:
        return _CRITIC_PROMPT_MAX
    if quality >= 7:
        return _CRITIC_PROMPT_HIGH
    return _CRITIC_PROMPT_BASE


async def critic(draft: str, quality: int = 5) -> str:
    """
    Reviews a draft and returns structured improvement feedback.

    The depth and focus of the review scales with the quality level:
    - 1–6  : basic grammar, structure, and flow check
    - 7–8  : professional standard — structure, completeness, clarity, tone
    - 9–10 : publication-ready — exhaustive evaluation across all dimensions
    """
    system_prompt = _get_critic_prompt(quality)

    feedback = await chat(system_prompt, draft)

    return feedback