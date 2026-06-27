
import time
import random
import asyncio
import traceback
from collections import deque

from agents.planner_agent import create_plan
from agents.retriever_agent import retrieve
from agents.analyzer_agent import analyze
from agents.writer_agent import write, stream_write
from agents.critic_agent import critic
from agents.quality_agent import improve


# ──────────────────────────────────────────────────────────────────────────────
# Timeout constants
# ──────────────────────────────────────────────────────────────────────────────

# Maximum seconds a single agent call (retrieve / analyze / write) may take
# before it is forcibly cancelled.
AGENT_CALL_TIMEOUT = 120  # seconds

# Maximum seconds to wait for the *next token* from a streaming writer before
# treating the stream as stalled and aborting it.
STREAM_TOKEN_INACTIVITY_TIMEOUT = 30  # seconds


# ──────────────────────────────────────────────────────────────────────────────
# Error classification
# ──────────────────────────────────────────────────────────────────────────────

def _classify_error(exc: Exception) -> str:
    """
    Maps an exception to a coarse error category so retry logic can
    respond appropriately instead of blindly retrying everything.

    Categories
    ----------
    rate_limit       → exponential back-off + jitter, worth retrying
    quota_exceeded   → fail fast — more retries won't help
    auth             → fail fast — credentials problem, not transient
    context_length   → retry with context trimming
    timeout          → moderate back-off, may be transient
    unknown          → default retry behaviour
    """
    msg = str(exc).lower()

    if any(k in msg for k in ("rate limit", "rate_limit", "429", "too many requests")):
        return "rate_limit"

    if any(k in msg for k in ("quota", "billing", "insufficient_quota", "402")):
        return "quota_exceeded"

    if any(k in msg for k in ("auth", "401", "403", "api key", "apikey", "unauthorized", "forbidden")):
        return "auth"

    if any(k in msg for k in ("context length", "context_length", "maximum context",
                               "token limit", "too long", "max_tokens", "prompt is too long")):
        return "context_length"

    if any(k in msg for k in ("timeout", "timed out", "asyncio", "deadline")):
        return "timeout"

    return "unknown"


def _should_retry(error_type: str) -> bool:
    """Returns False for error classes where retrying is pointless."""
    return error_type not in ("quota_exceeded", "auth")


async def _retry_delay(attempt: int, error_type: str, base_delay: float = 1.0) -> None:
    """
    Waits before a retry attempt.

    rate_limit  → exponential back-off with full jitter (capped at 60 s)
    timeout     → moderate fixed + small jitter
    everything  → linear base_delay * (attempt + 1)
    """
    if error_type == "rate_limit":
        cap = 60.0
        delay = min(cap, base_delay * (2 ** attempt)) * random.random()
    elif error_type == "timeout":
        delay = base_delay * 2 + random.uniform(0, 1)
    else:
        delay = base_delay * (attempt + 1)

    await asyncio.sleep(delay)


def _trim_context(results: dict) -> dict:
    """
    Best-effort context trimmer invoked when a context_length error
    is encountered. Truncates the `output` field of the largest results
    entries to reduce token pressure.

    This is intentionally conservative — it keeps structure intact so
    downstream agents still receive the right keys.
    """
    TRIM_THRESHOLD = 2000   # chars; trim outputs longer than this
    TRIM_TARGET = 1000       # chars to keep after trimming

    trimmed = {}
    for step, entry in results.items():
        if not isinstance(entry, dict):
            trimmed[step] = entry
            continue
        output = entry.get("output", "")
        if isinstance(output, str) and len(output) > TRIM_THRESHOLD:
            output = output[:TRIM_TARGET] + "\n... [trimmed for context length]"
        trimmed[step] = {**entry, "output": output}
    return trimmed


class Orchestrator:
    MAX_RETRIES = 2
    RETRY_DELAY = 1     # seconds — base, actual delay varies by error type
    MAX_CONCURRENCY = 5  # cap on parallel calls within a single batch

    # =========================================================================
    # Core agent runner with timeout + classified retry
    # =========================================================================

    async def run_agent(self, agent_name: str, func, *args):
        """
        Wraps a single async agent call with:
        - Per-call hard timeout (AGENT_CALL_TIMEOUT).
        - Error classification (rate_limit, auth, quota, context_length, …).
        - Differentiated retry strategy per error class:
            * quota / auth   → fail immediately (no point retrying)
            * rate_limit     → exponential back-off + full jitter
            * context_length → trim context snapshot (last positional arg
                               assumed to be results dict) then retry
            * others         → linear back-off
        - Full traceback logged on every failure for post-mortem analysis.
        """
        current_args = list(args)

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                output = await asyncio.wait_for(
                    func(*current_args),
                    timeout=AGENT_CALL_TIMEOUT
                )
                return {
                    "success": True,
                    "output": output,
                    "attempts": attempt + 1,
                    "error": None,
                    "error_type": None
                }

            except asyncio.TimeoutError as e:
                error_type = "timeout"
                err_str = (
                    f"{agent_name} timed out after {AGENT_CALL_TIMEOUT}s "
                    f"(Attempt {attempt + 1})"
                )
                print(err_str)

            except Exception as e:
                error_type = _classify_error(e)
                err_str = str(e)
                print(
                    f"{agent_name} failed [{error_type}] "
                    f"(Attempt {attempt + 1}): {err_str}"
                )
                traceback.print_exc()

                # Context-length: trim context and retry immediately
                if error_type == "context_length" and len(current_args) > 1:
                    print(f"[{agent_name}] Context too long — trimming context and retrying.")
                    current_args[-1] = _trim_context(current_args[-1])

            # Decide whether to retry
            if attempt < self.MAX_RETRIES and _should_retry(error_type):
                await _retry_delay(attempt, error_type, self.RETRY_DELAY)
            else:
                # Either exhausted retries or a non-retriable error class
                if not _should_retry(error_type):
                    print(
                        f"{agent_name} error type '{error_type}' is non-retriable. "
                        f"Failing immediately."
                    )
                return {
                    "success": False,
                    "output": None,
                    "attempts": attempt + 1,
                    "error": err_str,
                    "error_type": error_type
                }

        # Unreachable, but satisfies type-checkers
        return {
            "success": False,
            "output": None,
            "attempts": self.MAX_RETRIES + 1,
            "error": "Exhausted retries",
            "error_type": "unknown"
        }

    # =========================================================================
    # BATCHING HELPERS
    # =========================================================================

    def _build_consecutive_batches(self, tasks):
        """
        Original v1 heuristic (kept as fallback):
        Groups consecutive tasks that share the same agent type into a
        single concurrent batch.  A new batch starts whenever the agent
        type changes.

        Limitation: serialises independent steps that happen to be
        interleaved with different-agent steps.  Use
        `_build_dependency_batches` instead when tasks declare
        `depends_on`.
        """
        batches = []
        current_batch = []
        current_agent = None

        for task in tasks:
            if task.agent == current_agent:
                current_batch.append(task)
            else:
                if current_batch:
                    batches.append(current_batch)
                current_batch = [task]
                current_agent = task.agent

        if current_batch:
            batches.append(current_batch)

        return batches

    def _build_dependency_batches(self, tasks):
        """
        Topological-level scheduler (Kahn's algorithm — no external library).

        Each "level" of the topological sort becomes one concurrent batch.
        Tasks within a level have all their dependencies satisfied by
        earlier levels, so they can safely run in parallel regardless of
        agent type.

        Falls back to `_build_consecutive_batches` if:
        - No task declares `depends_on`, OR
        - A cycle is detected (prints a warning; broken plans run
          consecutively rather than crashing).

        Requirements on the Task model
        --------------------------------
        Task.depends_on: Optional[List[int]] = None
        Add this to models.py — until then the fallback always fires and
        behaviour is identical to v1.
        """
        # Check whether any task actually declares dependencies
        has_deps = any(
            getattr(t, "depends_on", None) for t in tasks
        )
        if not has_deps:
            return self._build_consecutive_batches(tasks)

        # Build step → task lookup
        step_to_task = {t.step: t for t in tasks}
        all_steps = set(step_to_task.keys())

        # Build adjacency: in-degree and reverse edges
        in_degree = {s: 0 for s in all_steps}
        dependents = {s: [] for s in all_steps}  # step → steps that depend on it

        for task in tasks:
            deps = getattr(task, "depends_on", None) or []
            for dep in deps:
                if dep not in all_steps:
                    print(
                        f"[Orchestrator] Warning: step {task.step} depends_on "
                        f"unknown step {dep} — ignoring that edge."
                    )
                    continue
                in_degree[task.step] += 1
                dependents[dep].append(task.step)

        # Kahn's BFS
        queue = deque(s for s in all_steps if in_degree[s] == 0)
        levels = []
        visited = 0

        while queue:
            # Drain the entire current frontier into one batch
            level_steps = list(queue)
            queue.clear()
            levels.append([step_to_task[s] for s in sorted(level_steps)])
            visited += len(level_steps)

            for step in level_steps:
                for dependent_step in dependents[step]:
                    in_degree[dependent_step] -= 1
                    if in_degree[dependent_step] == 0:
                        queue.append(dependent_step)

        if visited != len(tasks):
            # Cycle detected — fall back to consecutive batching
            print(
                "[Orchestrator] Warning: dependency cycle detected in plan. "
                "Falling back to consecutive-agent batching."
            )
            return self._build_consecutive_batches(tasks)

        return levels

    def _build_batches(self, tasks):
        """
        Public entry point — delegates to the topological scheduler when
        any task declares `depends_on`, otherwise uses the v1 consecutive
        heuristic.  Callers don't need to know which path was taken.
        """
        return self._build_dependency_batches(tasks)

    async def _gather_bounded(self, coros, max_concurrency=None):
        """
        Runs coroutines concurrently, but caps how many run at once so we
        don't blow through API rate limits when a batch is large.
        """
        sem = asyncio.Semaphore(max_concurrency or self.MAX_CONCURRENCY)

        async def _run(coro):
            async with sem:
                return await coro

        return await asyncio.gather(*(_run(c) for c in coros))

    # =========================================================================
    # NORMAL (non-streaming) EXECUTION
    # =========================================================================

    async def execute(self, user_request: str, quality: int = 5):

        plan = await create_plan(user_request)

        results = {}
        failures = []
        failed_count = 0
        final_draft = ""

        batches = self._build_batches(plan.tasks)

        for batch in batches:

            agent = batch[0].agent
            step_list = [t.step for t in batch]

            print(f"\nExecuting Step(s) {step_list}")
            print(f"Agent : {agent}")
            if len(batch) > 1:
                print(f"Running {len(batch)} '{agent}' tasks concurrently")

            # --------------------------------------------------
            # Unknown agent type — record and skip
            # --------------------------------------------------
            if agent not in ("retriever", "analyzer", "writer"):
                for task in batch:
                    print(f"Task  : {task.task}")
                    output = f"Unknown Agent : {task.agent}"
                    results[task.step] = {
                        "agent": task.agent,
                        "task": task.task,
                        "output": output
                    }
                continue

            # --------------------------------------------------
            # Snapshot results before the batch runs so all tasks
            # in the batch see the same prior context.
            # --------------------------------------------------
            snapshot = results.copy()

            if agent == "retriever":
                coros = [
                    self.run_agent("Retriever", retrieve, t.task)
                    for t in batch
                ]
            elif agent == "analyzer":
                coros = [
                    self.run_agent("Analyzer", analyze, t.task, snapshot)
                    for t in batch
                ]
            else:  # writer
                coros = [
                    self.run_agent("Writer", write, t.task, snapshot)
                    for t in batch
                ]

            batch_results = await self._gather_bounded(coros)

            for task, result in zip(batch, batch_results):
                if result["success"]:
                    output = result["output"]
                    if agent == "writer":
                        final_draft = output
                else:
                    failed_count += 1
                    failures.append({
                        "agent": agent,
                        "reason": result["error"],
                        "error_type": result.get("error_type", "unknown"),
                        "attempts": result.get("attempts", 1)
                    })
                    output = f"{agent.capitalize()} Failed."

                results[task.step] = {
                    "agent": task.agent,
                    "task": task.task,
                    "output": output
                }

        # ------------------------------------------
        # Quality Pipeline
        # ------------------------------------------

        passes = 0
        feedback = ""

        if quality >= 7:

            passes = 1

            if quality >= 8:
                passes = 2

            if quality == 10:
                passes = 3

            for i in range(passes):
                try:
                    feedback = await critic(final_draft)
                    final_draft = await improve(final_draft, feedback, quality)
                except Exception as e:
                    failures.append({
                        "agent": f"quality_pass_{i + 1}",
                        "reason": str(e),
                        "error_type": _classify_error(e)
                    })
                    # Keep the last good draft and continue

        results["quality"] = {
            "passes": passes,
            "critic_feedback": feedback,
            "final_output": final_draft
        }

        return {
            "plan": plan,
            "quality_level": quality,
            "failed_count": failed_count,
            "failures": failures,
            "results": results,
            "final_answer": final_draft
        }

    # =========================================================================
    # STREAMING EXECUTION
    # =========================================================================

    async def execute_stream(self, user_request: str, quality: int = 5):

        start_time = time.perf_counter()

        failures = []
        failed_count = 0

        # ------------------------------------------
        # Planner
        # ------------------------------------------

        yield {
            "type": "status",
            "agent": "planner",
            "message": "Creating execution plan..."
        }

        plan = await create_plan(user_request)

        yield {
            "type": "plan",
            "data": [
                {
                    "step": task.step,
                    "agent": task.agent,
                    "task": task.task,
                    "depends_on": getattr(task, "depends_on", None) or []
                }
                for task in plan.tasks
            ]
        }

        results = {}
        final_draft = ""

        batches = self._build_batches(plan.tasks)

        # =====================================================================
        # Execute Batches
        # =====================================================================

        for batch in batches:

            agent = batch[0].agent
            step_list = ", ".join(str(t.step) for t in batch)
            concurrent_note = " concurrently" if len(batch) > 1 else ""

            yield {
                "type": "status",
                "agent": agent,
                "message": f"Executing Step(s) {step_list}{concurrent_note}"
            }

            # --------------------------------------------------
            # Unknown agent type
            # --------------------------------------------------
            if agent not in ("retriever", "analyzer", "writer"):
                for task in batch:
                    output = f"Unknown Agent : {task.agent}"
                    results[task.step] = {
                        "agent": task.agent,
                        "task": task.task,
                        "output": output
                    }
                    yield {
                        "type": "agent_complete",
                        "agent": task.agent,
                        "step": task.step
                    }
                continue

            # --------------------------------------------------
            # Retriever / Analyzer — run concurrently, each task
            # emits its own agent_complete as it resolves.
            # --------------------------------------------------
            if agent in ("retriever", "analyzer"):

                snapshot = results.copy()

                if agent == "retriever":
                    coros = [
                        self.run_agent("Retriever", retrieve, t.task)
                        for t in batch
                    ]
                else:
                    coros = [
                        self.run_agent("Analyzer", analyze, t.task, snapshot)
                        for t in batch
                    ]

                batch_results = await self._gather_bounded(coros)

                for task, result in zip(batch, batch_results):
                    if result["success"]:
                        output = result["output"]
                    else:
                        failed_count += 1
                        failures.append({
                            "agent": agent,
                            "reason": result["error"],
                            "error_type": result.get("error_type", "unknown"),
                            "attempts": result.get("attempts", 1)
                        })
                        output = f"{agent.capitalize()} Failed."

                    results[task.step] = {
                        "agent": task.agent,
                        "task": task.task,
                        "output": output
                    }

                    yield {
                        "type": "agent_complete",
                        "agent": agent,
                        "step": task.step
                    }

            # --------------------------------------------------
            # Writer — intentionally sequential within the batch.
            # Streaming token-by-token from multiple writer agents
            # at once would interleave their output with no way for
            # the client to attribute which token belongs to which
            # step. Writers are processed one at a time.
            #
            # v1 bug fixed: writer now has full retry logic. On retry
            # a `writer_retry` event is emitted so the client knows a
            # fresh stream is starting (already-sent tokens from a
            # failed attempt cannot be unsent — this is the honest
            # and transparent way to surface a retry to the client).
            # --------------------------------------------------
            else:  # writer

                for task in batch:
                    writer_succeeded = False
                    writer_output = None

                    for attempt in range(self.MAX_RETRIES + 1):

                        if attempt > 0:
                            yield {
                                "type": "writer_retry",
                                "step": task.step,
                                "attempt": attempt + 1,
                                "message": (
                                    f"Writer retrying step {task.step} "
                                    f"(attempt {attempt + 1}/{self.MAX_RETRIES + 1})"
                                )
                            }

                        try:
                            token_buffer = []

                            async def _stream_with_inactivity_timeout(task_inner, results_snapshot):
                                """
                                Wraps stream_write so that if no token arrives
                                within STREAM_TOKEN_INACTIVITY_TIMEOUT seconds
                                the generator is treated as stalled.
                                """
                                async for event in stream_write(task_inner.task, results_snapshot):
                                    yield event

                            stalled = False
                            results_snapshot = results.copy()

                            async def _bounded_stream():
                                """Pulls events from stream_write with an inactivity deadline."""
                                nonlocal stalled
                                gen = stream_write(task.task, results_snapshot)
                                while True:
                                    try:
                                        event = await asyncio.wait_for(
                                            gen.__anext__(),
                                            timeout=STREAM_TOKEN_INACTIVITY_TIMEOUT
                                        )
                                        yield event
                                    except asyncio.TimeoutError:
                                        stalled = True
                                        raise StopAsyncIteration
                                    except StopAsyncIteration:
                                        return

                            async for event in _bounded_stream():

                                if event["type"] == "token":
                                    token_buffer.append(event["content"])
                                    yield {
                                        "type": "token",
                                        "content": event["content"]
                                    }

                                elif event["type"] == "writer_complete":
                                    writer_output = event["content"]
                                    writer_succeeded = True

                            if stalled:
                                raise asyncio.TimeoutError(
                                    f"Writer stream stalled for >{STREAM_TOKEN_INACTIVITY_TIMEOUT}s "
                                    f"with no new token."
                                )

                            if writer_succeeded:
                                break  # Exit retry loop on success

                            # stream_write finished but never emitted writer_complete
                            # Reconstruct from buffered tokens as a fallback
                            if token_buffer and not writer_succeeded:
                                writer_output = "".join(token_buffer)
                                writer_succeeded = True
                                print(
                                    f"[Writer] Step {task.step}: writer_complete event "
                                    f"missing — reconstructed output from token buffer."
                                )
                                break

                        except Exception as e:
                            error_type = _classify_error(e)
                            err_str = str(e)
                            print(
                                f"[Writer] Step {task.step} failed [{error_type}] "
                                f"(attempt {attempt + 1}): {err_str}"
                            )
                            traceback.print_exc()

                            if attempt < self.MAX_RETRIES and _should_retry(error_type):
                                await _retry_delay(attempt, error_type, self.RETRY_DELAY)
                                # Continue to next retry
                            else:
                                # Non-retriable or exhausted
                                failed_count += 1
                                failures.append({
                                    "agent": "writer",
                                    "reason": err_str,
                                    "error_type": error_type,
                                    "attempts": attempt + 1,
                                    "step": task.step
                                })
                                writer_output = "Writer Failed."
                                break

                    # Record result regardless of success/failure
                    final_output = writer_output if writer_output is not None else "Writer Failed."
                    if writer_succeeded and writer_output:
                        final_draft = writer_output

                    results[task.step] = {
                        "agent": task.agent,
                        "task": task.task,
                        "output": final_output
                    }

                    yield {
                        "type": "agent_complete",
                        "agent": "writer",
                        "step": task.step
                    }

        # =====================================================================
        # Quality Improvement
        # =====================================================================

        passes = 0
        feedback = ""

        try:
            if quality >= 7:

                passes = 1

                if quality >= 8:
                    passes = 2

                if quality == 10:
                    passes = 3

                yield {
                    "type": "status",
                    "agent": "critic",
                    "message": "Reviewing draft..."
                }

                for i in range(passes):

                    yield {
                        "type": "status",
                        "agent": "quality",
                        "message": f"Quality Pass {i + 1}"
                    }

                    try:
                        feedback = await critic(final_draft)
                        final_draft = await improve(final_draft, feedback, quality)
                    except Exception as e:
                        error_type = _classify_error(e)
                        failures.append({
                            "agent": f"quality_pass_{i + 1}",
                            "reason": str(e),
                            "error_type": error_type
                        })
                        # Keep the last good draft and continue

        except Exception as e:
            failures.append({
                "agent": "quality_pipeline",
                "reason": str(e),
                "error_type": _classify_error(e)
            })

        execution_time = round(
            time.perf_counter() - start_time,
            2
        )

        metadata = {
            "quality_level": quality,
            "passes": passes,
            "execution_time": execution_time,
            "steps": len(plan.tasks),
            "failed_count": failed_count,
            "failures": failures
        }

        yield {
            "type": "metadata",
            "data": metadata
        }

        yield {
            "type": "final",
            "data": {
                "plan": plan.model_dump(),  # Pydantic v2: serialize to plain dict for json.dumps
                "quality_level": quality,
                "results": results,
                "metadata": metadata,
                "final_answer": final_draft
            }
        }