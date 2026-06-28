# Agentic AI System

A simple multi-agent AI system that can solve complex user requests by breaking them into smaller tasks and assigning them to specialized AI agents.

## Live Demo

**Hosted URL:**
https://agentic-ai-system-production-9f94.up.railway.app/

---

## Features

* Multi-agent architecture
* Automatic task planning
* Parallel task execution
* Real-time response streaming (SSE)
* Retry mechanism for failed agents
* Quality improvement pipeline
* Execution metadata

---

## Workflow

```
User Request
      ↓
Planner Agent
      ↓
Retriever Agent
      ↓
Analyzer Agent
      ↓
Writer Agent
      ↓
Critic Agent (extra feature)
      ↓
Quality Agent (extra feature)
      ↓
Final Response
```

---

## Technology Stack

* Python
* FastAPI
* Groq API
* HTML, CSS, JavaScript
* Server-Sent Events (SSE)
* Railway

---

## Run Locally

```bash
git clone <repository-url>
cd agentic-ai-system

python -m venv env
env\Scripts\activate

pip install -r requirements.txt

uvicorn app:app --reload
```

Open:

```
http://127.0.0.1:8000
```

---

## Author

**Rohan Sukase**

Diploma in Artificial Intelligence and Machine Learning
