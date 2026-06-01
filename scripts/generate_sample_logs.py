#!/usr/bin/env python3
import json
import os
from datetime import datetime, timezone, timedelta

LOG_DIR = "logs"

def _ts(base: datetime, offset_ms: int = 0) -> str:
    return (base + timedelta(milliseconds=offset_ms)).isoformat()

def _log_line(ts: str, event: str, data: dict) -> str:
    return json.dumps({"timestamp": ts, "event": event, "data": data}, ensure_ascii=False)

def generate_sample(base: datetime):
    lines = []
    lines.append(_log_line(_ts(base, 0), "AGENT_START", {
        "input": "I want to buy 2 Wireless Earbuds", "model": "deepseek-chat", "version": "v2-json-actions", "max_steps": 5
    }))

    lines.append(_log_line(_ts(base, 1000), "LLM_RESPONSE", {
        "step": 1, "thought": "Check stock", "response": 'Action: {"tool": "check_stock", "args": {"product_id": "P001"}}',
        "latency_ms": 1000, "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120}
    }))
    lines.append(_log_line(_ts(base, 1000), "LLM_METRIC", {
        "provider": "openai", "model": "deepseek-chat", "prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120,
        "latency_ms": 1000, "cost_estimate": 0.001
    }))
    lines.append(_log_line(_ts(base, 1100), "TOOL_CALL", {
        "tool": "check_stock", "args": {"product_id": "P001"}, "observation": '{"available": true, "quantity": 10}'
    }))
    lines.append(_log_line(_ts(base, 1100), "AGENT_STEP", {
        "step": 1, "thought": "Check stock", "action": {"tool": "check_stock", "args": {"product_id": "P001"}}, "observation": '{"available": true}'
    }))
    return lines

def main() -> None:
    os.makedirs(LOG_DIR, exist_ok=True)
    base = datetime(2026, 6, 1, 9, 30, 0, tzinfo=timezone.utc)
    all_lines = generate_sample(base)
    
    log_file = os.path.join(LOG_DIR, f"{base.strftime('%Y-%m-%d')}.log")
    with open(log_file, "w", encoding="utf-8") as fh:
        for line in all_lines:
            fh.write(line + "\n")
    print(f"[OK] Generated {len(all_lines)} log entries -> {log_file}")

if __name__ == "__main__":
    main()
