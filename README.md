<div align="center">

```
 █████╗ ██████╗  ██████╗ ██╗   ██╗███████╗
██╔══██╗██╔══██╗██╔════╝ ██║   ██║██╔════╝
███████║██████╔╝██║  ███╗██║   ██║███████╗
██╔══██║██╔══██╗██║   ██║██║   ██║╚════██║
██║  ██║██║  ██║╚██████╔╝╚██████╔╝███████║
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝  ╚═════╝ ╚══════╝
```

**Autonomous AI Orchestrator with Planning, Execution, Memory, and Tool Use**

![Status](https://img.shields.io/badge/status-early%20alpha-orange?style=flat-square)
![Python](https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python&logoColor=white)
![LM Studio](https://img.shields.io/badge/LM%20Studio-local%20LLMs-green?style=flat-square)
![MCP](https://img.shields.io/badge/tools-MCP-purple?style=flat-square)

</div>

---

ARGUS is a multi-agent orchestration framework that combines a **reasoning planner**, an **action executor**, a **persistent task queue**, and **MCP-powered tools** into a single autonomous workflow. Unlike a chatbot, ARGUS breaks goals into tasks, runs them through tools, evaluates results, retries failures, and maintains state across sessions.

---

## How It Works

```
User Goal  →  Planner (reasons)  →  Task Queue  →  Executor (acts)  →  Re-plan
               ↑                                                          │
               └──────────────── evaluate result ◄────────────────────── ┘
```

| Component | Role |
|-----------|------|
| **Planner** | Reasoning LLM — breaks goals into tasks, reviews results, decides next steps. Never touches tools. |
| **Executor** | Tool-use LLM — receives tasks, fires MCP commands (shell, Docker, etc). Strictly action, no reasoning. |
| **Task Manager** | SQLite-backed priority queue with retries, failure tracking, and crash recovery. |
| **Memory** | Persistent execution history (Phase 1). Vector search + RAG coming in Phase 2. |

---

## Example Run

```bash
$ python orchestrator.py

Planner : ONLINE
Executor: ONLINE
Queue   : READY

Enter goal: check system health
```

```
Planner  → [1] Check system logs  [2] Check disk space  [3] Check memory usage

Executor → journalctl -n 50       → No critical errors found
Executor → df -h                  → Disk usage healthy
Executor → free -m                → Memory within limits

Planner  → Goal complete ✓
```

---

## Roadmap

**Done**
- [x] Planner / Executor separation
- [x] Persistent task queue (SQLite)
- [x] MCP execution support
- [x] LM Studio integration
- [x] Retry system + session recovery

**In Progress**
- [ ] Failure-aware replanning
- [ ] Better task decomposition
- [ ] Tool result evaluation

**Planned**
- [ ] Multi-executor / distributed workers
- [ ] Long-term memory + vector search (RAG)
- [ ] Agent collaboration
- [ ] Web interaction + filesystem indexing

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| Language | Python 3.10+ |
| Planner LLM | LM Studio — Mistral 7B / Qwen / Llama / DeepSeek |
| Executor LLM | LM Studio MCP — Qwen 2.5 |
| Tools | MCP + Docker MCP Gateway |
| Storage | SQLite |

---

## Project Structure

```
argus/
├── planner/          # Reasoning model + prompts
├── executor/         # Tool-use model + prompts
├── tasks/            # Task dataclass, queue, history
├── memory/           # Task store + RAG stub
├── utils/            # LM Studio client, logger, helpers
├── config/           # Settings
├── data/             # task_history.db
└── orchestrator.py   # Control loop
```

---

## Vision

ARGUS is designed as an **autonomous operator**, not a conversational assistant. The long-term goal is a system that plans, executes, learns from failure, uses tools, and maintains memory — while remaining **model-agnostic** and **fully local**.

---

<div align="center">
<sub>Early Alpha · Actively evolving · Contributions welcome</sub>
</div>
