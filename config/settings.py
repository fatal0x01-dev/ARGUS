"""
Central configuration for the orchestrator system.
Edit these values to match your local setup.
"""

# ─── LM Studio Endpoints ────────────────────────────────────────────────────

PLANNER_API_URL = "http://localhost:1234/v1"      # LM Studio API
EXECUTOR_API_URL = "http://localhost:1234"      # LM Studio API
LMSTUDIO_API_TOKEN = "TOKEN_HERE"

# ─── Model Names ────────────────────────────────────────────────────────────
# Must match the model identifier shown in LM Studio

PLANNER_MODEL = "mistral-7b-instruct-v0.1"         # e.g. "qwen3-30b"
EXECUTOR_MODEL = "qwen2.5-7b-instruct-uncensored"        # e.g. "qwen2.5-72b"

# ─── LM Studio Request Settings ─────────────────────────────────────────────

PLANNER_TEMPERATURE = 0.4
EXECUTOR_TEMPERATURE = 0.2
REQUEST_TIMEOUT = 120                              # seconds per API call
MAX_TOKENS = 32768

# ─── Orchestrator Loop Settings ─────────────────────────────────────────────

MAX_ITERATIONS = 50                               # hard safety cap
MAX_TASK_RETRIES = 3                              # retries before marking FAILED

# ─── Database ────────────────────────────────────────────────────────────────

import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
TASK_DB_PATH = os.path.join(DATA_DIR, "task_history.db")

# ─── Logging ─────────────────────────────────────────────────────────────────

LOG_LEVEL = "INFO"                                # DEBUG | INFO | WARNING | ERROR
LOG_TO_FILE = True
LOG_FILE = os.path.join(DATA_DIR, "orchestrator.log")