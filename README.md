# Coding Agent 

An agentic AI system that writes, executes, and fixes code autonomously. Built with LangGraph and Groq (Llama 3.3 70B). Supports Python, SQL, and C++.

## Demo

> Coming soon — will add screen recording after UI polish

## What it does

- Takes a coding problem in plain English
- Writes code to solve it
- Executes the code in a sandboxed environment
- If it fails, reads the error and fixes it automatically
- Repeats until the code works or hits max iterations

## Architecture

## Tech Stack

| Layer | Technology |
|---|---|
| Agent Orchestration | LangGraph |
| LLM | Groq — Llama 3.3 70B Versatile |
| Memory | ChromaDB (vector store) |
| UI | Streamlit |
| Python Execution | subprocess (sandboxed) |
| SQL Execution | SQLAlchemy + SQLite |
| C++ Execution | g++ compiler + subprocess |
| Deployment | Railway (coming soon) |

## Project Structure

## Getting Started

### Prerequisites

- Python 3.11
- Git
- Groq API key (free at [console.groq.com](https://console.groq.com))
- g++ compiler (for C++ support)

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/coding-agent.git
cd coding-agent

# Create and activate virtual environment
python -m venv .venv

# Windows
source .venv/Scripts/activate

# Mac/Linux
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Set up environment variables

```bash
cp .env.example .env
```

Open `.env` and add your Groq API key:

### Run

```bash
streamlit run ui/app.py
```

Open `http://localhost:8501` in your browser.

## Usage Examples

**Python:**
> "Write a function that checks if a number is prime"

**SQL:**
> "Create a users table and insert 3 records, then query them"

**C++:**
> "Write a program that prints the Fibonacci sequence up to 100"

## Design Decisions

**Why LangGraph over plain LangChain?**
LangGraph gives explicit control over the agent loop as a state machine. This makes the fix-and-retry loop predictable and debuggable — you can see exactly which node is running at every step.

**Why Groq?**
Groq's inference speed is significantly faster than other providers, which matters a lot in an agent loop where the LLM is called multiple times per task. It's also free.

**Why SQLite for SQL execution?**
Zero setup, file-based, and sufficient for demonstrating SQL capabilities. Can be swapped for PostgreSQL with a one-line change in `sql_executor.py`.

**Why subprocess for Python execution?**
Isolates the executed code from the main process. Prevents user code from crashing the agent or accessing the agent's memory.

## Roadmap

- [ ] ChromaDB memory — agent remembers past solutions
- [ ] Test-driven loop — writes failing test first, then fixes until green
- [ ] Docker sandboxing for C++ — resource limits and network isolation
- [ ] Streaming output — see agent thinking in real time
- [ ] Cloud deployment to Railway

## License

MIT