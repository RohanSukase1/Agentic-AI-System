import json
import re
import asyncio

from models import Plan
from utils.llm import chat

PLANNER_SYSTEM_PROMPT = """
You are a Planning Agent inside a multi-agent AI system.

IMPORTANT:

You DO NOT answer the user's request.

You ONLY create an execution plan.

Never research.

Never summarize.

Never compare.

Never write blogs.

Never write LinkedIn posts.

Your only responsibility is decomposing a request into ordered tasks.

Available agents:

retriever
- search information
- retrieve facts

analyzer
- compare
- summarize
- analyze

writer
- write articles
- reports
- LinkedIn posts

Dependency declaration (optional but recommended for parallelism):
- Each task may include a "depends_on" field: a list of step numbers that must complete before this task runs.
- If two retriever tasks are fully independent, do NOT add depends_on between them — this lets them run concurrently.
- If an analyzer task needs results from multiple retrievers, list all of them in depends_on.

Example with dependencies:

{
    "tasks":[
        {
            "step":1,
            "agent":"retriever",
            "task":"Research Tesla AI products",
            "depends_on":[]
        },
        {
            "step":2,
            "agent":"retriever",
            "task":"Research OpenAI AI products",
            "depends_on":[]
        },
        {
            "step":3,
            "agent":"analyzer",
            "task":"Compare Tesla AI products with OpenAI AI products",
            "depends_on":[1,2]
        },
        {
            "step":4,
            "agent":"writer",
            "task":"Write a LinkedIn post based on the comparison",
            "depends_on":[3]
        }
    ]
}

Return JSON only.

No explanation.

No markdown.

No code fences.

No <think> or <thinking> tags.
"""

PLANNER_REPAIR_PROMPT = """
Your previous response could not be parsed as valid JSON.

Parse error: {error}

Your previous response was:
---
{bad_response}
---

Return ONLY the corrected JSON object. No explanation, no markdown, no code fences, no thinking tags.
"""

MAX_PLAN_RETRIES = 2
PLAN_RETRY_DELAY = 1  # seconds


def _strip_reasoning_tags(text: str) -> str:
    """
    Removes <think>...</think> and <thinking>...</thinking> blocks
    emitted by reasoning/chain-of-thought models (e.g. DeepSeek-R1,
    QwQ, o1-style fine-tunes) before attempting JSON parsing.
    Strips lazily so nested content is preserved where possible.
    """
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<thinking>.*?</thinking>", "", text, flags=re.DOTALL | re.IGNORECASE)
    return text.strip()


def _strip_markdown_fences(text: str) -> str:
    """
    Removes ```json ... ``` and ``` ... ``` fences that some models
    add despite being told not to.
    """
    # Remove opening fence (with optional language tag)
    text = re.sub(r"^```(?:json)?\s*\n?", "", text.strip(), flags=re.IGNORECASE)
    # Remove closing fence
    text = re.sub(r"\n?```\s*$", "", text.strip(), flags=re.IGNORECASE)
    return text.strip()


def _extract_json_object(text: str) -> str:
    """
    Last-resort extractor: finds the outermost { ... } substring.
    Handles cases where the model prepended a sentence or left a
    trailing comment after the JSON object.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return text[start:end + 1]
    return text


def _normalize_response(response) -> str:
    """
    Defensively converts whatever chat() returns into a plain string.
    Handles: str, dict (OpenAI-style), list of content blocks
    (Anthropic-style), or anything with a .text / .content attribute.
    """
    if isinstance(response, str):
        return response
    if isinstance(response, dict):
        # OpenAI chat completion dict
        try:
            return response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            pass
        # Anthropic message dict
        try:
            blocks = response.get("content", [])
            return " ".join(
                b["text"] for b in blocks if b.get("type") == "text"
            )
        except (AttributeError, TypeError):
            pass
        return str(response)
    if isinstance(response, list):
        # List of content blocks
        parts = []
        for block in response:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block["text"])
            elif isinstance(block, str):
                parts.append(block)
        return " ".join(parts) if parts else str(response)
    # SDK response object with .text or .content
    if hasattr(response, "text"):
        return response.text
    if hasattr(response, "content"):
        content = response.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(
                b.text for b in content if hasattr(b, "text")
            )
    return str(response)


def _clean_response(raw: str) -> str:
    """
    Full cleaning pipeline: reasoning tags → markdown fences → trim.
    """
    text = _normalize_response(raw)
    text = _strip_reasoning_tags(text)
    text = _strip_markdown_fences(text)
    return text.strip()


def _parse_plan(text: str) -> Plan:
    """
    Attempts JSON parse of cleaned text, falling back to outermost-{}
    extraction. Raises ValueError with a descriptive message on failure.
    """
    # Attempt 1: direct parse
    try:
        data = json.loads(text)
        return Plan(**data)
    except (json.JSONDecodeError, Exception):
        pass

    # Attempt 2: extract outermost { ... }
    extracted = _extract_json_object(text)
    try:
        data = json.loads(extracted)
        return Plan(**data)
    except Exception as e:
        raise ValueError(
            f"Could not parse plan JSON.\n"
            f"Cleaned text was:\n{text}\n\n"
            f"Parse error: {e}"
        )


def _validate_plan(plan: Plan) -> None:
    """
    Basic sanity checks on the produced plan.
    Raises ValueError if the plan is structurally invalid.
    """
    if not plan.tasks:
        raise ValueError("Planner returned an empty task list.")

    steps = [t.step for t in plan.tasks]

    # Steps must be unique
    if len(steps) != len(set(steps)):
        raise ValueError(f"Planner returned duplicate step numbers: {steps}")

    # Steps should be sequential starting from 1 (warn but don't crash)
    expected = list(range(1, len(steps) + 1))
    if sorted(steps) != expected:
        # Non-fatal — log and continue; orchestrator uses dict keyed by step
        print(
            f"[Planner] Warning: steps are not sequential 1..N. "
            f"Got {sorted(steps)}, expected {expected}. Continuing anyway."
        )


async def create_plan(user_request: str) -> Plan:
    """
    Generates an execution plan from a user request.

    Improvements over v1:
    - Normalizes whatever chat() returns (str, dict, SDK object).
    - Strips <think>/<thinking> blocks from reasoning models.
    - Strips markdown code fences.
    - Falls back to outermost-{} extraction before giving up.
    - On parse failure: sends a repair turn to the model with the exact
      error, up to MAX_PLAN_RETRIES times.
    - Validates the resulting plan for basic structural correctness.
    """

    raw_response = None
    last_error = None

    for attempt in range(MAX_PLAN_RETRIES + 1):

        if attempt == 0:
            # First attempt: normal planner call
            try:
                raw_response = await chat(PLANNER_SYSTEM_PROMPT, user_request)
            except Exception as e:
                last_error = f"chat() raised an exception: {e}"
                if attempt < MAX_PLAN_RETRIES:
                    await asyncio.sleep(PLAN_RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    raise Exception(
                        f"Planner failed after {MAX_PLAN_RETRIES + 1} attempts. "
                        f"Last error: {last_error}"
                    )
        else:
            # Repair turn: re-prompt with the exact error
            repair_prompt = PLANNER_REPAIR_PROMPT.format(
                error=last_error,
                bad_response=_normalize_response(raw_response) if raw_response else "(no response)"
            )
            print(
                f"[Planner] Repair attempt {attempt}/{MAX_PLAN_RETRIES} "
                f"due to: {last_error}"
            )
            try:
                raw_response = await chat(PLANNER_SYSTEM_PROMPT, repair_prompt)
            except Exception as e:
                last_error = f"chat() raised an exception during repair: {e}"
                if attempt < MAX_PLAN_RETRIES:
                    await asyncio.sleep(PLAN_RETRY_DELAY * (attempt + 1))
                    continue
                else:
                    raise Exception(
                        f"Planner repair failed after {MAX_PLAN_RETRIES} attempts. "
                        f"Last error: {last_error}"
                    )

        cleaned = _clean_response(raw_response)

        try:
            plan = _parse_plan(cleaned)
            _validate_plan(plan)
            if attempt > 0:
                print(f"[Planner] Repair succeeded on attempt {attempt}.")
            return plan

        except ValueError as e:
            last_error = str(e)
            if attempt < MAX_PLAN_RETRIES:
                await asyncio.sleep(PLAN_RETRY_DELAY * (attempt + 1))
                # Loop back for a repair turn
                continue
            else:
                raise Exception(
                    f"Planner returned unparseable output after "
                    f"{MAX_PLAN_RETRIES + 1} attempts.\n\n"
                    f"Last cleaned response:\n{cleaned}\n\n"
                    f"Last error: {last_error}"
                )

    # Should never reach here, but satisfy type-checker
    raise Exception("Planner: exhausted all attempts without returning a plan.")