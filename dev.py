#!/usr/bin/env python3
import subprocess
import sys

backend = subprocess.Popen(
    ["osascript", "-e",
     'tell app "Terminal" to do script "cd /Users/vmiu/Documents/Code/copinvest && uv run uvicorn backend.main:app --reload --port 8000"']
)

frontend = subprocess.Popen(
    ["osascript", "-e",
     'tell app "Terminal" to do script "cd /Users/vmiu/Documents/Code/copinvest/frontend && npm run dev"']
)

backend.wait()
frontend.wait()
