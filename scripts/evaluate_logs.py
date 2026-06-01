#!/usr/bin/env python3
import json
import os
import argparse
from typing import List, Dict, Any

def _percentile(sorted_values: List[float], pct: float) -> float:
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[f]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])

class MetricsCollector:
    def __init__(self):
        self.runs = 0
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0
        self.latencies = []
        self.errors = 0
        self.tool_usage = {}
        self.total_cost = 0.0

    def process_event(self, event_type: str, data: Dict[str, Any]):
        if event_type == "AGENT_START":
            self.runs += 1
        elif event_type == "LLM_METRIC":
            self.total_prompt_tokens += data.get("prompt_tokens", 0)
            self.total_completion_tokens += data.get("completion_tokens", 0)
            self.total_tokens += data.get("total_tokens", 0)
            if "latency_ms" in data:
                self.latencies.append(data["latency_ms"])
            self.total_cost += data.get("cost_estimate", 0.0)
        elif event_type == "TOOL_CALL":
            tool_name = data.get("tool", "unknown")
            self.tool_usage[tool_name] = self.tool_usage.get(tool_name, 0) + 1
        elif event_type in ("PARSE_ERROR", "TOOL_ERROR"):
            self.errors += 1

def main():
    parser = argparse.ArgumentParser(description="Evaluate Agent Logs")
    parser.add_argument("--log-dir", default="logs", help="Directory containing JSONL logs")
    parser.add_argument("--format", choices=["text", "md"], default="text", help="Output format")
    parser.add_argument("--output", help="Output file path (optional)")
    args = parser.parse_args()

    collector = MetricsCollector()
    parsed_events = 0
    files_processed = 0

    if not os.path.exists(args.log_dir):
        print(f"Directory {args.log_dir} not found.")
        return

    for filename in os.listdir(args.log_dir):
        if filename.endswith(".log"):
            files_processed += 1
            with open(os.path.join(args.log_dir, filename), "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        event = json.loads(line)
                        collector.process_event(event.get("event"), event.get("data", {}))
                        parsed_events += 1
                    except json.JSONDecodeError:
                        continue

    collector.latencies.sort()
    avg_latency = sum(collector.latencies) / len(collector.latencies) if collector.latencies else 0
    p50 = _percentile(collector.latencies, 50)
    p90 = _percentile(collector.latencies, 90)
    p99 = _percentile(collector.latencies, 99)

    out_str = []
    if args.format == "text":
        out_str.append(f"[INFO] Parsed {parsed_events} events from {files_processed} log file(s).")
        out_str.append("============================================================")
        out_str.append("  AGENT TELEMETRY — EVALUATION REPORT")
        out_str.append("============================================================")
        out_str.append(f"  Total Agent Runs       : {collector.runs}")
        out_str.append(f"  Total Errors           : {collector.errors}")
        out_str.append(f"  Total Prompt Tokens    : {collector.total_prompt_tokens:,}")
        out_str.append(f"  Total Completion Tokens: {collector.total_completion_tokens:,}")
        out_str.append(f"  Total Tokens           : {collector.total_tokens:,}")
        out_str.append(f"  Average Latency        : {avg_latency:,.0f} ms")
        out_str.append(f"  P50 Latency            : {p50:,.0f} ms")
        out_str.append(f"  P99 Latency            : {p99:,.0f} ms")
        out_str.append(f"  Estimated Cost         : ${collector.total_cost:.4f}")
        out_str.append("── Tool Usage ──────────────────────────────────────")
        for tool, count in collector.tool_usage.items():
            out_str.append(f"    {tool:20} : {count} calls")
    else:
        out_str.append("# Agent Telemetry Evaluation Report")
        out_str.append(f"| Metric | Value |")
        out_str.append(f"|---|---|")
        out_str.append(f"| Runs | {collector.runs} |")
        out_str.append(f"| Errors | {collector.errors} |")
        out_str.append(f"| Total Tokens | {collector.total_tokens:,} |")
        out_str.append(f"| Avg Latency | {avg_latency:,.0f} ms |")
        out_str.append(f"| P99 Latency | {p99:,.0f} ms |")
        out_str.append(f"| Cost | ${collector.total_cost:.4f} |")

    final_output = "\n".join(out_str)
    print(final_output)
    
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(final_output)
        print(f"\n[INFO] Report written to {args.output}")

if __name__ == "__main__":
    main()
