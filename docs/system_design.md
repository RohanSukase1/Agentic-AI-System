# System Design Document
## Agentic AI System

---

## What is this system?

This is an AI system where you type a complex request and it automatically figures out what steps to take, runs those steps using different specialized AI agents, and gives you a final written answer — all while showing you what's happening in real time.

For example if you type:
> "Research Tesla and OpenAI, compare them, and write a LinkedIn post"

The system will:
1. Break that into 4 tasks automatically
2. Search for Tesla info
3. Search for OpenAI info
4. Compare both
5. Write the LinkedIn post

---

## How it works (simple version)

```
You type a request
       ↓
Planner reads it and makes a task list
       ↓
Tasks are sent to the right agents
       ↓
Retriever → finds information
Analyzer  → compares / summarizes
Writer    → writes the final output
       ↓
(Optional) Critic reviews it → Quality agent improves it
       ↓
Final answer shown to you
```

---

## The agents

I built 6 agents. Each one has one job and does nothing else.

**Planner**
- Reads your request
- Returns a JSON list of tasks with step numbers
- Each task says which agent should do it and what it should do

**Retriever**
- Gets a task like "research Tesla AI products"
- Searches and returns relevant information as text

**Analyzer**
- Gets a task like "compare Tesla and OpenAI"
- Looks at what the Retriever found
- Returns a summary or comparison

**Writer**
- Gets a task like "write a LinkedIn post based on the comparison"
- Looks at all previous results
- Writes the final content
- Streams it word by word so you see it appear in real time

**Critic**
- Reviews the Writer's draft
- Returns structured feedback (what's good, what's bad, what to fix)

**Quality Agent**
- Takes the draft + critic feedback
- Rewrites it to be better
- Only runs if quality level is 7 or above

---

## The Orchestrator

This is the main file that controls everything. Think of it as the manager.

It does these things in order:

1. Checks if your message is just a greeting like "hello" — if yes, replies directly without running any agents
2. Calls the Planner to get the task list
3. Figures out which tasks can run at the same time (tasks with no dependencies run together)
4. Runs each batch of tasks
5. Sends each word of the Writer's output to your browser as it's generated
6. Runs the quality pipeline if quality level is high enough
7. Sends final metadata (how long it took, how many steps, any failures)

---

## How tasks run in parallel

The Planner assigns a `depends_on` field to each task. For example:

```
Step 1 - Retriever - "Research Tesla"     - depends_on: []
Step 2 - Retriever - "Research OpenAI"    - depends_on: []
Step 3 - Analyzer  - "Compare both"       - depends_on: [1, 2]
Step 4 - Writer    - "Write LinkedIn post" - depends_on: [3]
```

Steps 1 and 2 have no dependencies so they run at the same time.
Step 3 waits for 1 and 2 to finish.
Step 4 waits for 3 to finish.

This saves time instead of running everything one by one.

---

## How streaming works

Instead of waiting for the entire answer to be ready before showing it, the Writer sends each word to the browser as soon as it's generated using Server-Sent Events (SSE).

SSE is basically a one-way connection where the server keeps pushing small messages to the browser. Each message is one word or chunk of text.

The browser receives these and appends them to the output area in real time — so you see the text appearing as it's being written.

---

## Error handling

If an agent fails, the system doesn't crash. It:

1. Logs what went wrong
2. Retries up to 2 times
3. Waits a bit before retrying (longer wait if it's a rate limit error)
4. If it still fails, marks that step as failed and moves on
5. Shows you at the end which steps failed and why

Different errors are handled differently:
- Rate limit → wait and retry
- Wrong API key → fail immediately, no point retrying
- Timeout → retry with a short wait
- Response too long → trim it and retry

---

## Quality levels

The user picks a quality level from 1 to 10.

| Level | What happens |
|---|---|
| 1–6 | Just writes the draft, no review |
| 7 | One round of critic + improve |
| 8–9 | Two rounds of critic + improve |
| 10 | Three rounds of critic + improve |

Higher quality = slower but better output.

---

## Tech used

| What | Technology |
|---|---|
| Backend | Python, FastAPI |
| LLM | Groq API |
| Frontend | Plain HTML, CSS, JavaScript |
| Streaming | Server-Sent Events (SSE) |
| Hosting | Railway |

---

## Folder structure

```
agentic-ai/
├── app.py              ← server, handles HTTP requests
├── orchestrator.py     ← controls all the agents
├── models.py           ← defines what a Plan and Task look like
├── agents/
│   ├── planner_agent.py
│   ├── retriever_agent.py
│   ├── analyzer_agent.py
│   ├── writer_agent.py
│   ├── critic_agent.py
│   └── quality_agent.py
├── utils/
│   └── llm.py          ← sends requests to Groq API
└── index.html          ← the frontend UI
```

---

## What I would improve with more time

- Add memory so the system remembers previous conversations
- Let users see which agent is running in more detail
- Add support for file uploads so agents can read PDFs or documents
- Better UI for showing which steps passed and which failed
