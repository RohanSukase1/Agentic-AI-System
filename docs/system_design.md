# System Design Document
## Agentic AI System for Multi-Step Tasks

---

## 1. Overview

This system takes a complicated request from a user, breaks it down into simple steps using a special tool called a Planning Agent. It then sends each step to a different expert agent - like a Retriever, Analyzer, or Writer - to get the job done. As each step is completed, it shares the results with the user right away. Finally, it puts all the pieces together to create a finished product, and if needed, it can even make some last-minute improvements to make sure everything is just right.

Our system is designed from the ground up, without using any pre-built frameworks that we can't see inside. Instead, we've written every part of it - from planning to routing, batching, retrying, streaming, and quality control - directly in Python and FastAPI. This means we have complete control over how everything works, and we can make sure each component does exactly what we need it to.

---

## 2. Architecture

### 2.1 High-Level Components

```
User Request
│
▼
┌─────────────┐
│  FastAPI    │  ← HTTP + Server-Sent Events (SSE)
│  app.py     │
└──────┬──────┘
│
▼
┌─────────────────────────────────────────────┐
│              Orchestrator                   │
│                                             │
│  ┌──────────────┐   ┌────────────────────┐  │
│  │ Conversational│   │  Planner Agent     │  │
│  │   Shortcut   │   │  (create_plan)     │  │
│  └──────────────┘   └────────┬───────────┘  │
│                              │ Plan (JSON)   │
│                    ┌─────────▼──────────┐   │
│                    │  Batch Scheduler   │   │
│                    │  (Kahn's algorithm)│   │
│                    └─────────┬──────────┘   │
│                              │              │
│           ┌──────────────────┼──────────────┤
│           ▼                  ▼              ▼
│   ┌───────────────┐  ┌───────────┐  ┌────────────┐
│   │   Retriever   │  │ Analyzer  │  │   Writer   │
│   │   Agent       │  │  Agent    │  │   Agent    │
│   └───────────────┘  └───────────┘  └────────────┘
│                                            │
│                              ┌─────────────▼──────┐
│                              │  Quality Pipeline  │
│                              │  Critic → Improve  │
│                              └─────────────┬──────┘
└────────────────────────────────────────────┼───────┘
│
▼
Final Answer
(streamed via SSE)
```

### 2.2 Component Responsibilities

| Component | File | Responsibility |
|---|---|---|
| FastAPI Server | `app.py` | Accepts HTTP requests, streams SSE events to the browser |
| Coordinator | `coordinator.py` | This is the main part that controls all the other parts, it handles batches, retries, and streaming, making sure everything runs smoothly |
| Planner Agent | `agents/planner_agent.py` | Decomposes user request into a structured JSON task plan |
| Retriever Agent | `agents/retriever_agent.py` | Searches for and retrieves relevant information |
| Analyzer Agent | `agents/analyzer_agent.py` | Compares, summarizes, and draws conclusions from retrieved data |
| Writer Agent | `agents/writer_agent.py` | Produces the final written output; supports token streaming |
| Critic Agent | `agents/critic_agent.py` | Reviews the draft and produces structured improvement feedback |
| Quality Agent | `agents/quality_agent.py` | Improves the draft based on feedback from critics to reach a certain level of quality |
| LLM Utility | `utils/llm.py` | Thin async wrapper around the Groq API |
| Frontend | `index.html` | Single-page UI; renders the execution plan, streams tokens, shows metadata |

---

## 3. Data Flow

### 3.1 Normal Agentic Request

```
1. User types request → POST /stream (SSE endpoint)

2. Orchestrator checks _is_conversational(request)
└─ If greeting/trivial → _direct_chat() → stream reply → done
└─ If agentic → continue

3. Planner Agent called:
└─ LLM produces JSON plan: [{step, agent, task, depends_on}, ...]
The plan has been checked and it's good to go - there are no empty lists, no duplicate steps, and the steps are in the right order.
└─ `plan` SSE event emitted → frontend renders execution timeline

4. Batch Scheduler (Kahn's topological sort):
└─ Tasks with no dependencies → Batch 1 (run concurrently)
Here are the tasks that are ready to run at the same time, now that the things they depend on are done.
└─ ... and so on

5. For each batch:
When multiple tasks are run at the same time using asyncio.gather, it calls the retrieve function all at once.
└─ Analyzer tasks → analyze(task, results_snapshot) concurrently
└─ Writer tasks   → stream_write(task, results_snapshot) sequentially
└─ Each token → `token` SSE event → browser renders in real time

6. Quality Pipeline (if quality >= 7):
└─ critic(draft, quality)  → structured feedback
└─ improve(draft, feedback, quality) → refined draft
└─ Repeated N times based on quality level (1–3 passes)

7. `metadata` SSE event → execution time, pass count, failure summary
8. `final` SSE event     → full result object
```

### 3.2 SSE Event Types

| Event Type | Payload | Frontend Action |
|---|---|---|
| `status` | `{agent, message}` | Updates status bar |
| `plan` | `[{step, agent, task, depends_on}]` | Renders execution timeline |
| `agent_complete` | `{agent, step}` | Marks timeline step as done |
| `token` | `{content}` | Appends token to output area |
| `writer_retry` | `{step, attempt, message}` | Shows retry notification |
| `metadata` | `{quality_level, passes, execution_time, ...}` | Shows run summary |
| `final` | `{plan, results, final_answer, metadata}` | Marks run complete |

---

## 4. Key Design Decisions

### 4.1 No Black-Box Framework
The system does not use LangChain, AutoGen, CrewAI, or any similar framework. Every agent is a plain Python async function. The orchestrator, batching logic, retry policy, and SSE streaming are all written explicitly. This means every behavior is traceable, debuggable, and modifiable without reverse-engineering a framework.

### 4.2 Manual Batching with Topological Sort
The planner emits a `depends_on` field per task. The orchestrator implements Kahn's BFS algorithm (no external library) to group tasks into levels — tasks in the same level have no dependency on each other and run concurrently via `asyncio.gather`. This maximises throughput without needing a task queue.

### 4.3 Classified Error Handling
When things go wrong, mistakes can be grouped into five types before figuring out what to do next.

| Class | Strategy |
|---|---|
| `rate_limit` | Exponential back-off with full jitter, up to 60s, worth retrying |
If you've exceeded your quota, trying again won't work. You've reached your limit, so you need to stop and figure out what to do next.
| `auth` | Fail immediately — credentials problem |
If the context is too long, try shortening it and then try again.
| `timeout` | It has a moderate fixed delay and a small amount of jitter |
| `unknown` | Linear back-off |

This avoids wasting time retrying quota or auth errors and prevents thundering-herd on rate limits.

### 4.4 Streaming Architecture
The Writer agent relies on `stream_write()`, which is an asynchronous generator that produces tokens as it receives them from the LLM. As soon as each token is generated, it's immediately sent to the browser as an SSE event. To prevent stalled streams, an inactivity watchdog is used, which aborts the stream if there's no activity for a certain period of time - in this case, 30 seconds. If the `writer_complete` event is missing for some reason, the output is reconstructed from the token buffer as a fallback, ensuring that the output is still generated even if the stream is incomplete. This process helps to maintain a stable and continuous flow of data from the Writer agent to the browser.

### 4.5 Quality Pipeline
Quality is a user-controlled integer (1–10). The orchestrator maps this to:
- A writer hint injected into the task description (calibrates the first draft)
- A number of critic → improve passes (0 for quality ≤ 6, up to 3 for quality 10)
- A tiered system prompt for both the critic and improve agents

---

## 5. Deployment

| Layer | Technology |
|---|---|
| Backend | Python 3.10, FastAPI, Uvicorn |
| LLM Provider | Groq API (async client) |
| Frontend | Vanilla HTML/CSS/JS, Server-Sent Events |
| Hosting | Railway (auto-deploy from GitHub) |
| Environment | `GROQ_API_KEY` via Railway environment variables |

---

## 6. Repository Structure

```
agentic-ai/
├── app.py                   # FastAPI server, SSE endpoint
├── orchestrator.py          # Core coordination logic
├── models.py                # Pydantic models (Plan, Task)
├── requirements.txt
├── agents/
│   ├── planner_agent.py     # Task decomposition
│   ├── retriever_agent.py   # Information retrieval
│   ├── analyzer_agent.py    # Analysis and comparison
│   ├── writer_agent.py      # Content generation (streaming)
│   ├── critic_agent.py      # Draft review
│   └── quality_agent.py     # Draft improvement
├── utils/
│   └── llm.py               # Groq async wrapper
└── index.html               # Single-page frontend
```