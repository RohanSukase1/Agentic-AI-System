# Agentic AI System

An AI system that takes a complex request, breaks it into steps, and handles each step with a specialized agent — all while streaming the output to you in real time.

---

## What it does

You give it a task like *"Research GPT-4 and Gemini, compare them, and write a blog post"* and it:

1. Figures out what steps are needed
2. Runs each step with the right agent (Retriever, Analyzer, or Writer)
3. Streams the final output to you word by word
4. Optionally polishes the result based on a quality level you set

---

## Agents

- **Planner** — reads your request and creates an ordered task list
- **Retriever** — finds and pulls in relevant information
- **Analyzer** — compares, summarizes, and draws conclusions
- **Writer** — writes the final output (blog post, report, LinkedIn post, etc.)
- **Critic** — reviews the draft and gives specific feedback
- **Quality Agent** — rewrites the draft based on that feedback

---

## Getting started

**1. Clone the repo**
```bash
git clone https://github.com/your-username/agentic-ai.git
cd agentic-ai
```

**2. Install dependencies**
```bash
pip install -r requirements.txt
```

**3. Add your API key**

Create a `.env` file in the root folder:
```
GROQ_API_KEY=your_key_here
```

Get a free key at [console.groq.com](https://console.groq.com)

**4. Run it**
```bash
uvicorn app:app --reload
```

Then open `http://localhost:8000` in your browser.

---

## How to use it

1. Type your request in the input box
2. Adjust the quality slider (1 = fast draft, 10 = polished output)
3. Hit send and watch the plan appear, then the output stream in

Simple messages like "hello" or "thanks" skip the pipeline and just get a normal reply.

---

## Project structure

```
├── app.py                  # the server
├── orchestrator.py         # coordinates everything
├── models.py               # data models
├── agents/
│   ├── planner_agent.py
│   ├── retriever_agent.py
│   ├── analyzer_agent.py
│   ├── writer_agent.py
│   ├── critic_agent.py
│   └── quality_agent.py
├── utils/
│   └── llm.py              # Groq API wrapper
└── index.html              # frontend
```

---

## Deploying

This runs on [Railway](https://railway.app). Push to GitHub, connect the repo on Railway, add your `GROQ_API_KEY` in the environment variables, and it's live.

---

## A few things worth knowing

- It won't crash if one agent fails — it logs the failure and keeps going
- Rate limit errors are retried automatically with back-off
- The quality pipeline only kicks in at quality level 7 and above
- No LangChain, no AutoGen — everything is written from scratch