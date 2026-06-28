# Post-Mortem Document
## Agentic AI System for Multi-Step Tasks

---

## 1. One Scaling Issue Encountered

### The Problem: Single Groq API Key Becomes a Bottleneck Under Concurrent Users

During development and testing, the system worked well for one user at a time. However, when multiple users send requests simultaneously, all of their agent calls share the same Groq API key. Groq enforces per-key rate limits (requests per minute and tokens per minute). When several users each trigger a plan with 4–6 agent steps running in parallel, the total number of concurrent API calls spikes rapidly — easily hitting the rate limit within seconds.

The current handling for this is `_classify_error("rate_limit")` → exponential back-off with full jitter. This is correct for a single user hitting a brief limit, but under real concurrent load it creates a compounding problem: every user's agents start backing off simultaneously, jitter only helps partially, and long waits degrade all users' experience at once.

### What I Would Do at Scale

- Implement a **token bucket or sliding window rate limiter** in `utils/llm.py` that is shared across all in-flight requests within the server process. This limits outgoing Groq calls to a safe rate before they hit the provider limit, eliminating error-driven back-off entirely.
- For higher scale: introduce a **request queue** (e.g. Redis + a worker pool) so that incoming agent tasks are queued and dispatched at a controlled rate rather than all fired simultaneously.
- Use **multiple API keys** (separate Groq accounts or provider accounts) with round-robin distribution to multiply throughput linearly.

---

## 2. One Design Change I Would Make in Hindsight

### What I Would Change: Give the Planner Access to a Schema of What Each Agent Can Actually Return

Currently, the Planner Agent knows only that agents exist and what their names are. It writes task descriptions in natural language — for example: *"Research Tesla's latest AI products"* for the Retriever, and *"Compare Tesla AI with OpenAI AI"* for the Analyzer.

The problem this creates is that the Analyzer receives a task description that refers to information from the Retriever by name, but it receives the actual output through the `results` dict keyed by step number. If the Planner writes step 3 as *"Compare step 1 and step 2 results"*, the Analyzer has to infer which keys in the `results` dict are relevant. This works most of the time, but produces vague or off-target analysis when the plan is complex or steps are numbered unexpectedly.

**The change:** I would add a lightweight context-injection step in the Orchestrator — before calling the Analyzer or Writer, the orchestrator would build a structured `context` string that explicitly maps step numbers to their output summaries, and prepend it to the agent's task prompt. This removes the ambiguity entirely and makes agent calls more deterministic and higher quality, without requiring any changes to the LLM or the agent functions themselves.

---

## 3. Two Explicit Trade-Offs

### Trade-Off 1: Streaming vs. Structured Output

**Decision made:** The Writer agent streams tokens directly to the browser as they are generated, rather than waiting for the complete output before sending it.

**Why:** Streaming makes the system feel fast and responsive. Users see words appearing within 1–2 seconds of the writer starting, rather than staring at a spinner for 15–30 seconds waiting for a complete response. For a system that can take 30–90 seconds end-to-end, this dramatically improves perceived performance.

**What it costs:** Streaming adds significant implementation complexity. We need an async generator (`stream_write`), an inactivity watchdog timeout, a token buffer fallback for when the `writer_complete` event is missing, and sequential (not concurrent) handling of multiple writer tasks because interleaved token streams from two simultaneous writers cannot be attributed separately by the frontend. All of this is code that can break in ways that a simple `await write(task)` call cannot.

**Reasoning:** The trade-off is worth it. The UX gain from streaming is large and immediately visible to every user on every request. The complexity is real but isolated to a single section of the orchestrator and the writer agent, and it has been carefully handled with fallbacks.

---

### Trade-Off 2: Stateless Agents vs. Shared Memory

**Decision made:** Each agent is a stateless async function. Agents do not share state directly — they communicate only through the `results` dict that the Orchestrator maintains and passes as a snapshot to downstream agents.

**Why:** Stateless agents are simple, testable, and safe to run concurrently. There is no risk of one agent corrupting another's state mid-execution, no need for locks or semaphores between agents, and each agent function can be tested in isolation with a simple mock of the `results` dict.

**What it costs:** The Analyzer and Writer receive only the outputs of prior steps, not the internal reasoning or intermediate states of those steps. If the Retriever found ten relevant facts but only surfaced five in its output (because of length limits), the Analyzer never sees the other five. Information that doesn't make it into the `results` dict is permanently lost to downstream agents. A shared memory store (e.g. a Redis key-value store or an in-process dictionary with richer structure) would allow agents to write intermediate findings that other agents could selectively query.

**Reasoning:** For the current scope of the system — a single-user, single-session request processed in one pipeline run — stateless agents with a passed snapshot are the right default. Shared memory would add operational complexity (what if an agent writes bad data to shared state? how do we isolate one user's state from another's?) that is not justified until the system needs cross-session memory or multi-user collaboration features. This is a deliberate starting point, not an oversight.