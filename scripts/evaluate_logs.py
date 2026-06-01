#!/usr/bin/env python3
"""evaluate_logs.py — Parse agent JSON logs and compute aggregate metrics.

Reads every ``*.log`` file under the ``logs/`` directory, extracts JSONL
events emitted by :class:`IndustryLogger`, and prints a summary report
covering:

- **Token usage** (prompt / completion / total)
- **Latency** (P50, P90, P99)
- **Loop counts** (average steps per run, max-steps rate)
- **Error analysis** (parse errors, tool errors, loop guards)
- **Cost estimate**
- **Success rate**

Usage::

    python scripts/evaluate_logs.py                # default logs/ dir
    python scripts/evaluate_logs.py --log-dir logs  # explicit path
    python scripts/evaluate_logs.py --format md      # markdown table output
"""

import argparse
import glob
import json
import os
import sys
from collections import Counter
from typing import Any, Dict, List, Optional


# ── Helpers ────────────────────────────────────────────────────────────────────

def _percentile(sorted_values: List[float], pct: float) -> float:
    """Return the *pct*-th percentile from a pre-sorted list."""
    if not sorted_values:
        return 0.0
    k = (len(sorted_values) - 1) * (pct / 100.0)
    f = int(k)
    c = f + 1
    if c >= len(sorted_values):
        return sorted_values[f]
    return sorted_values[f] + (k - f) * (sorted_values[c] - sorted_values[f])


def _parse_log_file(path: str) -> List[Dict[str, Any]]:
    """Read a log file and return list of parsed JSON events.

    Lines that are not valid JSON are silently skipped.
    """
    events: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            # Handle lines that might be prefixed by Python logging metadata
            # e.g. "INFO:AI-Lab-Agent:{...}" — find the first '{' character
            brace = line.find("{")
            if brace == -1:
                continue
            candidate = line[brace:]
            try:
                obj = json.loads(candidate)
                if isinstance(obj, dict) and "event" in obj:
                    events.append(obj)
            except json.JSONDecodeError:
                continue
    return events


# ── Metric collectors ─────────────────────────────────────────────────────────

class MetricsCollector:
    """Accumulate metrics from parsed log events."""

    def __init__(self):
        self.latencies: List[float] = []
        self.prompt_tokens: List[int] = []
        self.completion_tokens: List[int] = []
        self.total_tokens: List[int] = []
        self.costs: List[float] = []
        self.steps_per_run: List[int] = []
        self.run_statuses: Counter = Counter()
        self.error_types: Counter = Counter()
        self.tool_calls: Counter = Counter()
        self.total_runs = 0

    def ingest(self, events: List[Dict[str, Any]]) -> None:
        """Process a list of events."""
        for ev in events:
            event_type = ev.get("event", "")
            data = ev.get("data", {})

            if event_type == "LLM_METRIC":
                self._handle_llm_metric(data)
            elif event_type == "AGENT_START":
                self.total_runs += 1
            elif event_type == "AGENT_END":
                self._handle_agent_end(data)
            elif event_type == "TOOL_CALL":
                tool_name = data.get("tool", "unknown")
                self.tool_calls[tool_name] += 1
            elif event_type in ("PARSE_ERROR", "TOOL_ERROR", "UNKNOWN_TOOL"):
                self.error_types[event_type] += 1
            elif event_type == "LOOP_GUARD":
                self.error_types["LOOP_GUARD"] += 1
            elif event_type == "MAX_STEPS":
                self.error_types["MAX_STEPS"] += 1
            elif event_type == "LLM_RESPONSE":
                latency = data.get("latency_ms", 0)
                if latency:
                    self.latencies.append(float(latency))
                usage = data.get("usage", {})
                if usage:
                    self.prompt_tokens.append(usage.get("prompt_tokens", 0))
                    self.completion_tokens.append(usage.get("completion_tokens", 0))
                    self.total_tokens.append(usage.get("total_tokens", 0))

    def _handle_llm_metric(self, data: Dict[str, Any]) -> None:
        latency = data.get("latency_ms", 0)
        if latency:
            self.latencies.append(float(latency))
        self.prompt_tokens.append(data.get("prompt_tokens", 0))
        self.completion_tokens.append(data.get("completion_tokens", 0))
        self.total_tokens.append(data.get("total_tokens", 0))
        self.costs.append(data.get("cost_estimate", 0.0))

    def _handle_agent_end(self, data: Dict[str, Any]) -> None:
        status = data.get("status", "unknown")
        self.run_statuses[status] += 1
        steps = data.get("steps", 0)
        if steps:
            self.steps_per_run.append(steps)

    # ── Computed metrics ──────────────────────────────────────────────

    @property
    def total_prompt_tokens(self) -> int:
        return sum(self.prompt_tokens)

    @property
    def total_completion_tokens(self) -> int:
        return sum(self.completion_tokens)

    @property
    def total_total_tokens(self) -> int:
        return sum(self.total_tokens)

    @property
    def avg_tokens_per_call(self) -> float:
        return self.total_total_tokens / max(1, len(self.total_tokens))

    @property
    def latency_p50(self) -> float:
        s = sorted(self.latencies)
        return _percentile(s, 50)

    @property
    def latency_p90(self) -> float:
        s = sorted(self.latencies)
        return _percentile(s, 90)

    @property
    def latency_p99(self) -> float:
        s = sorted(self.latencies)
        return _percentile(s, 99)

    @property
    def avg_latency(self) -> float:
        return sum(self.latencies) / max(1, len(self.latencies))

    @property
    def avg_steps(self) -> float:
        return sum(self.steps_per_run) / max(1, len(self.steps_per_run))

    @property
    def total_cost(self) -> float:
        return sum(self.costs)

    @property
    def success_count(self) -> int:
        return self.run_statuses.get("success", 0)

    @property
    def success_rate(self) -> float:
        if self.total_runs == 0:
            return 0.0
        return (self.success_count / self.total_runs) * 100.0

    @property
    def total_errors(self) -> int:
        return sum(self.error_types.values())


# ── Formatters ─────────────────────────────────────────────────────────────────

def _format_text(mc: MetricsCollector) -> str:
    lines = [
        "=" * 60,
        "  AGENT TELEMETRY — EVALUATION REPORT",
        "=" * 60,
        "",
        f"  Total Agent Runs       : {mc.total_runs}",
        f"  Success Rate           : {mc.success_rate:.1f}% ({mc.success_count}/{mc.total_runs})",
        f"  Avg Steps per Run      : {mc.avg_steps:.1f}",
        "",
        "── Token Usage ──────────────────────────────────────",
        f"  Total Prompt Tokens    : {mc.total_prompt_tokens:,}",
        f"  Total Completion Tokens: {mc.total_completion_tokens:,}",
        f"  Total Tokens           : {mc.total_total_tokens:,}",
        f"  Avg Tokens per Call    : {mc.avg_tokens_per_call:,.0f}",
        "",
        "── Latency (ms) ────────────────────────────────────",
        f"  Average                : {mc.avg_latency:,.0f} ms",
        f"  P50 (Median)           : {mc.latency_p50:,.0f} ms",
        f"  P90                    : {mc.latency_p90:,.0f} ms",
        f"  P99                    : {mc.latency_p99:,.0f} ms",
        f"  Total LLM Calls        : {len(mc.latencies)}",
        "",
        "── Cost ────────────────────────────────────────────",
        f"  Estimated Total Cost   : ${mc.total_cost:.4f}",
        "",
        "── Error Analysis ──────────────────────────────────",
        f"  Total Errors           : {mc.total_errors}",
    ]
    for etype, count in mc.error_types.most_common():
        lines.append(f"    {etype:20s} : {count}")
    lines.append("")
    lines.append("── Tool Usage ──────────────────────────────────────")
    for tool, count in mc.tool_calls.most_common():
        lines.append(f"    {tool:20s} : {count} calls")
    lines.append("")
    lines.append("── Run Outcomes ────────────────────────────────────")
    for status, count in mc.run_statuses.most_common():
        lines.append(f"    {status:20s} : {count}")
    lines.append("=" * 60)
    return "\n".join(lines)


def _format_markdown(mc: MetricsCollector) -> str:
    lines = [
        "# Agent Telemetry — Evaluation Report",
        "",
        "## Overview",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Total Agent Runs | {mc.total_runs} |",
        f"| Success Rate | {mc.success_rate:.1f}% ({mc.success_count}/{mc.total_runs}) |",
        f"| Avg Steps per Run | {mc.avg_steps:.1f} |",
        "",
        "## Token Usage",
        "",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Total Prompt Tokens | {mc.total_prompt_tokens:,} |",
        f"| Total Completion Tokens | {mc.total_completion_tokens:,} |",
        f"| Total Tokens | {mc.total_total_tokens:,} |",
        f"| Avg Tokens per LLM Call | {mc.avg_tokens_per_call:,.0f} |",
        "",
        "## Latency",
        "",
        "| Percentile | Latency (ms) |",
        "| :--- | :--- |",
        f"| Average | {mc.avg_latency:,.0f} |",
        f"| P50 (Median) | {mc.latency_p50:,.0f} |",
        f"| P90 | {mc.latency_p90:,.0f} |",
        f"| P99 | {mc.latency_p99:,.0f} |",
        "",
        "## Cost",
        "",
        f"- **Estimated Total Cost**: ${mc.total_cost:.4f}",
        "",
        "## Error Analysis",
        "",
        "| Error Type | Count |",
        "| :--- | :--- |",
    ]
    for etype, count in mc.error_types.most_common():
        lines.append(f"| {etype} | {count} |")
    if not mc.error_types:
        lines.append("| _(none)_ | 0 |")
    lines += [
        "",
        "## Tool Usage",
        "",
        "| Tool | Calls |",
        "| :--- | :--- |",
    ]
    for tool, count in mc.tool_calls.most_common():
        lines.append(f"| `{tool}` | {count} |")
    if not mc.tool_calls:
        lines.append("| _(none)_ | 0 |")
    lines += [
        "",
        "## Run Outcomes",
        "",
        "| Status | Count |",
        "| :--- | :--- |",
    ]
    for status, count in mc.run_statuses.most_common():
        lines.append(f"| {status} | {count} |")
    if not mc.run_statuses:
        lines.append("| _(none)_ | 0 |")
    return "\n".join(lines)


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse agent JSON logs and compute aggregate metrics."
    )
    parser.add_argument(
        "--log-dir",
        default="logs",
        help="Directory containing *.log files (default: logs/)",
    )
    parser.add_argument(
        "--format",
        choices=["text", "md"],
        default="text",
        help="Output format: text (console) or md (Markdown)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Write output to file instead of stdout.",
    )
    args = parser.parse_args()

    log_dir = args.log_dir
    if not os.path.isdir(log_dir):
        print(f"[ERROR] Log directory '{log_dir}' does not exist.", file=sys.stderr)
        print("Run the agent first to generate logs, e.g.:", file=sys.stderr)
        print("  python demo.py --max-steps 5", file=sys.stderr)
        sys.exit(1)

    log_files = sorted(glob.glob(os.path.join(log_dir, "*.log")))
    if not log_files:
        print(f"[WARNING] No .log files found in '{log_dir}'.", file=sys.stderr)
        sys.exit(0)

    collector = MetricsCollector()
    total_events = 0
    for path in log_files:
        events = _parse_log_file(path)
        total_events += len(events)
        collector.ingest(events)

    print(f"[INFO] Parsed {total_events} events from {len(log_files)} log file(s).", file=sys.stderr)

    if args.format == "md":
        output = _format_markdown(collector)
    else:
        output = _format_text(collector)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(output + "\n")
        print(f"[INFO] Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
