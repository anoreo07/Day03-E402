"""
demo.py – ReAct Agent Evaluation Demo
======================================
Runs the e-commerce ReAct Agent against the lab test cases and produces:
  1. Step-by-step Thought → Action → Observation trace (verbose)
  2. Per-case metrics summary: steps, tokens, latency, status
  3. Aggregate evaluation table (Chatbot vs Agent comparison)
  4. Optional Markdown report in report/

Satisfies:
  - EVALUATION.md  → Token efficiency, latency, loop count, failure analysis
  - INSTRUCTOR_GUIDE.md → ReAct trace, failure traces, provider switching demo
  - SCORING.md     → Trace quality, evaluation & analysis, live demo quality

Run:
    python demo.py                       # defaults to local provider
    python demo.py --provider openai
    python demo.py --provider gemini
    python demo.py --report              # also saves report/agent_eval_report.md
    python demo.py "Custom question?"    # run a single custom question
"""

import argparse
import os
import sys
import time
from datetime import datetime
from typing import List, Dict, Any, Optional

# ─── Load .env early (before other imports that might need env vars) ──────────
def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv as std_load
        std_load()
        return
    except ImportError:
        pass
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split("=", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    val = parts[1].strip().strip('"').strip("'")
                    os.environ[key] = val

_load_dotenv()

from src.agent.agent import ReActAgent
from src.core.provider_factory import build_provider_from_env
from src.tools import get_ecommerce_tools
from chatbot import BaselineChatbot

# ─── Lab Test Cases ───────────────────────────────────────────────────────────
AGENT_TEST_CASES: List[Dict[str, str]] = [
    {
        "id": "TC-A1",
        "desc": "Multi-step: stock check + coupon + tax + shipping (Hanoi)",
        "question": "I want to buy 2 Wireless Earbuds with coupon SAVE10 and ship to Hanoi. Is it in stock and what is the total?",
    },
    {
        "id": "TC-A2",
        "desc": "Multi-step: stock check + invalid coupon + tax + shipping (Ho Chi Minh)",
        "question": "Can I buy 3 Gaming Keyboards with coupon WINNER and ship to Ho Chi Minh? Give the final cost breakdown.",
    },
    {
        "id": "TC-A3",
        "desc": "Open-ended search: find product by keyword + price + tax + shipping (Da Nang)",
        "question": "Find a backpack product, then price 1 unit with tax and shipping to Da Nang.",
    },
]

# Baseline chatbot test questions (same intent as agent cases)
CHATBOT_TEST_QUESTIONS: List[str] = [
    "Mua 2 cái P001 dùng mã SUMMER10, tổng bao nhiêu?",
    "Mua 3 cái P019 dùng mã KEYBOARD15, tổng bao nhiêu?",
    "Mua 1 cái P004 dùng mã BACKPACK15, tổng bao nhiêu?",
]

# ─── Pretty print helpers ─────────────────────────────────────────────────────
W = 70

def _hr(char: str = "─") -> None:
    print(char * W)

def _header(title: str) -> None:
    _hr("═")
    print(f"  {title}")
    _hr("═")

def _section(title: str) -> None:
    _hr()
    print(f"  {title}")
    _hr()

# ─── Agent run with metric capture ───────────────────────────────────────────
def run_agent_case(agent: ReActAgent, tc: Dict[str, str], verbose: bool) -> Dict[str, Any]:
    """Run one test case and return metrics + result."""
    print(f"\n{'─'*W}")
    print(f"  [{tc['id']}] {tc['desc']}")
    print(f"{'─'*W}")
    print(f"  ❓ User: {tc['question']}")

    # Patch the tracker so we can read back the per-run usage
    from src.telemetry.metrics import tracker
    metrics_before = len(tracker.session_metrics)

    t0 = time.perf_counter()
    answer = agent.run(tc["question"])
    elapsed = (time.perf_counter() - t0) * 1000  # ms

    # Collect metrics emitted during this run
    run_metrics = tracker.session_metrics[metrics_before:]

    total_tokens  = sum(m["total_tokens"]  for m in run_metrics)
    prompt_tokens = sum(m["prompt_tokens"] for m in run_metrics)
    comp_tokens   = sum(m["completion_tokens"] for m in run_metrics)
    avg_latency   = (sum(m["latency_ms"] for m in run_metrics) / len(run_metrics)) if run_metrics else 0
    steps         = len(run_metrics)
    cost          = sum(m.get("cost_estimate", 0) for m in run_metrics)

    # Determine outcome
    if "Max steps reached" in answer or "loop_guard" in answer.lower():
        status = "⚠️  MAX_STEPS / LOOP"
    elif "ERROR" in answer:
        status = "❌ ERROR"
    else:
        status = "✅ SUCCESS"

    print(f"\n  💬 Final: {answer}")
    print(f"\n  📊 Metrics:")
    print(f"     Status         : {status}")
    print(f"     Steps (LLM calls) : {steps}")
    print(f"     Total tokens   : {total_tokens}  (prompt={prompt_tokens}, completion={comp_tokens})")
    print(f"     Avg latency/step : {avg_latency:.0f} ms")
    print(f"     Total time     : {elapsed:.0f} ms")
    print(f"     Cost estimate  : ${cost:.5f}")

    return {
        "id": tc["id"],
        "desc": tc["desc"],
        "question": tc["question"],
        "answer": answer,
        "status": status,
        "steps": steps,
        "total_tokens": total_tokens,
        "prompt_tokens": prompt_tokens,
        "comp_tokens": comp_tokens,
        "avg_latency_ms": avg_latency,
        "total_ms": elapsed,
        "cost": cost,
    }

# ─── Baseline chatbot comparison ──────────────────────────────────────────────
def run_chatbot_cases() -> List[Dict[str, Any]]:
    """Run baseline chatbot on comparable queries and return results."""
    bot = BaselineChatbot()
    results = []
    for question in CHATBOT_TEST_QUESTIONS:
        t0 = time.perf_counter()
        answer = bot.respond(question)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        results.append({
            "question": question,
            "answer": answer,
            "elapsed_ms": elapsed_ms,
        })
    return results

# ─── Report generation ────────────────────────────────────────────────────────
def generate_report(
    provider_name: str,
    model_name: str,
    agent_results: List[Dict[str, Any]],
    chatbot_results: List[Dict[str, Any]],
    output_path: str,
) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    passed   = sum(1 for r in agent_results if "SUCCESS" in r["status"])
    total    = len(agent_results)
    avg_steps = sum(r["steps"] for r in agent_results) / total if total else 0
    avg_tok  = sum(r["total_tokens"] for r in agent_results) / total if total else 0
    avg_lat  = sum(r["avg_latency_ms"] for r in agent_results) / total if total else 0

    lines = [
        f"# Agent Evaluation Report",
        f"",
        f"**Provider**: `{provider_name}` · **Model**: `{model_name}`  ",
        f"**Run date**: {now}",
        f"",
        f"---",
        f"",
        f"## 1. Agent Test Results",
        f"",
        f"| ID | Description | Status | Steps | Tokens | Avg Latency |",
        f"|----|-------------|--------|-------|--------|-------------|",
    ]
    for r in agent_results:
        lines.append(
            f"| {r['id']} | {r['desc']} | {r['status']} | {r['steps']} | {r['total_tokens']} | {r['avg_latency_ms']:.0f} ms |"
        )

    lines += [
        f"",
        f"**Pass rate**: {passed}/{total} ({passed/total*100:.0f}%)  ",
        f"**Avg steps/case**: {avg_steps:.1f}  ",
        f"**Avg tokens/case**: {avg_tok:.0f}  ",
        f"**Avg latency/step**: {avg_lat:.0f} ms",
        f"",
        f"---",
        f"",
        f"## 2. Detailed Traces",
        f"",
    ]
    for r in agent_results:
        lines += [
            f"### {r['id']}",
            f"",
            f"**Question**: {r['question']}",
            f"",
            f"**Answer**: {r['answer']}",
            f"",
            f"*(Full step-by-step trace is in `logs/` JSON file)*",
            f"",
        ]

    lines += [
        f"---",
        f"",
        f"## 3. Evaluation Metrics (EVALUATION.md)",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Token efficiency (avg prompt tokens) | {sum(r['prompt_tokens'] for r in agent_results)/total:.0f} |",
        f"| Token efficiency (avg completion tokens) | {sum(r['comp_tokens'] for r in agent_results)/total:.0f} |",
        f"| Avg steps to resolution | {avg_steps:.1f} |",
        f"| Avg step latency | {avg_lat:.0f} ms |",
        f"| Total cost estimate | ${sum(r['cost'] for r in agent_results):.5f} |",
        f"",
        f"---",
        f"",
        f"## 4. Chatbot Baseline vs ReAct Agent (SCORING.md)",
        f"",
        f"| Capability | Baseline Chatbot | ReAct Agent |",
        f"|------------|-----------------|-------------|",
        f"| Simple stock check | ✅ Keyword dispatch | ✅ Tool call |",
        f"| Apply coupon code | ✅ Keyword dispatch | ✅ Tool call |",
        f"| Multi-step total (discount+tax+ship) | ⚠️ Hardcoded pipeline | ✅ Dynamic loop |",
        f"| Search product by keyword (open-ended) | ❌ Not supported | ✅ search_products tool |",
        f"| Handle ambiguous / unknown intent | ❌ Fallback message | ✅ Reasons and recovers |",
        f"| Self-correct after tool error | ❌ No | ✅ Retries with observation |",
        f"| No LLM API needed | ✅ | ❌ |",
        f"",
    ]

    if chatbot_results:
        lines += [
            f"### Chatbot Baseline Answers",
            f"",
        ]
        for i, r in enumerate(chatbot_results, 1):
            lines += [
                f"**Q{i}**: {r['question']}",
                f"",
                f"**A{i}**: {r['answer'][:200]}{'...' if len(r['answer']) > 200 else ''}",
                f"",
                f"*Elapsed: {r['elapsed_ms']:.1f} ms (pure keyword dispatch, no LLM)*",
                f"",
            ]

    lines += [
        f"---",
        f"",
        f"*Report auto-generated by `demo.py`*",
    ]

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"\n  📄 Report saved → {output_path}")

# ─── Main ─────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="E-Commerce ReAct Agent – Evaluation Demo",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--provider",
        choices=["local", "openai", "gemini", "google", "scripted"],
        default="local",
        help="LLM provider to use. Default: local (GGUF via llama-cpp).",
    )
    parser.add_argument(
        "--model", default=None,
        help="Override model name (e.g. gpt-4o, gemini-1.5-flash).",
    )
    parser.add_argument(
        "--max-steps", type=int, default=8,
        help="Max ReAct loop steps per question. Default: 8.",
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Hide step-by-step ReAct trace output.",
    )
    parser.add_argument(
        "--report", action="store_true",
        help="Save an evaluation Markdown report to report/agent_eval_report.md.",
    )
    parser.add_argument(
        "--no-chatbot", action="store_true",
        help="Skip chatbot baseline comparison.",
    )
    parser.add_argument(
        "question", nargs="*",
        help="Optional custom question(s) to run instead of default test cases.",
    )
    args = parser.parse_args()

    # ── Build LLM ──────────────────────────────────────────────────────────
    _header("E-Commerce ReAct Agent – Evaluation Demo")
    print(f"  Provider : {args.provider.upper()}")
    print(f"  Max steps: {args.max_steps}")
    print(f"  Time     : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    llm = build_provider_from_env(args.provider, args.model)
    print(f"  Model    : {llm.model_name}")

    # ── Build agent ────────────────────────────────────────────────────────
    agent = ReActAgent(
        llm=llm,
        tools=get_ecommerce_tools(),
        max_steps=args.max_steps,
        verbose=not args.quiet,
    )

    # ── Choose test cases ──────────────────────────────────────────────────
    if args.question:
        test_cases = [
            {"id": f"CUSTOM-{i+1}", "desc": "Custom question", "question": q}
            for i, q in enumerate(args.question)
        ]
    else:
        test_cases = AGENT_TEST_CASES

    # ── Run Agent on test cases ────────────────────────────────────────────
    _section(f"Phase 1: Running {len(test_cases)} Agent Test Cases")
    agent_results = []
    for tc in test_cases:
        result = run_agent_case(agent, tc, verbose=not args.quiet)
        agent_results.append(result)

    # ── Agent Summary Table ────────────────────────────────────────────────
    _section("Phase 2: Aggregate Evaluation Summary (EVALUATION.md)")
    passed = sum(1 for r in agent_results if "SUCCESS" in r["status"])
    print(f"\n  {'ID':<10} {'Status':<22} {'Steps':>5} {'Tokens':>7} {'Avg ms':>8}  Description")
    print(f"  {'─'*10} {'─'*22} {'─'*5} {'─'*7} {'─'*8}  {'─'*28}")
    for r in agent_results:
        print(
            f"  {r['id']:<10} {r['status']:<22} {r['steps']:>5} "
            f"{r['total_tokens']:>7} {r['avg_latency_ms']:>7.0f}ms  {r['desc'][:35]}"
        )

    total = len(agent_results)
    print(f"\n  ✅ Pass rate    : {passed}/{total} ({passed/total*100:.0f}%)")
    print(f"  📐 Avg steps    : {sum(r['steps'] for r in agent_results)/total:.1f} per case")
    print(f"  🔤 Avg tokens   : {sum(r['total_tokens'] for r in agent_results)/total:.0f} per case")
    print(f"  ⚡ Avg latency  : {sum(r['avg_latency_ms'] for r in agent_results)/total:.0f} ms per step")
    print(f"  💰 Total cost   : ${sum(r['cost'] for r in agent_results):.5f}")

    # ── Failure Analysis ───────────────────────────────────────────────────
    failed = [r for r in agent_results if "SUCCESS" not in r["status"]]
    if failed:
        _section("Phase 3: Failure Analysis (EVALUATION.md)")
        for r in failed:
            print(f"\n  ❌ [{r['id']}] {r['status']}")
            print(f"     Question: {r['question']}")
            print(f"     Answer  : {r['answer'][:200]}")
            print(f"     → Check logs/ for full trace to diagnose the failure.")
    else:
        _section("Phase 3: Failure Analysis")
        print("  All cases passed – no failures to analyze.")
        print("  Tip: Check logs/*.log for full JSON traces and token usage details.")

    # ── Chatbot Baseline Comparison ────────────────────────────────────────
    if not args.no_chatbot and not args.question:
        _section("Phase 4: Chatbot Baseline vs ReAct Agent (SCORING.md)")
        print("  Running baseline chatbot on comparable queries...")
        chatbot_results = run_chatbot_cases()

        print(f"\n  {'Capability':<42} {'Chatbot':^12} {'ReAct Agent':^14}")
        print(f"  {'─'*42} {'─'*12} {'─'*14}")
        capabilities = [
            ("Simple stock check",                     "✅ keyword",  "✅ tool call"),
            ("Apply coupon code",                       "✅ keyword",  "✅ tool call"),
            ("Multi-step total (discount+tax+ship)",    "⚠️ hardcoded", "✅ dynamic"),
            ("Search product by keyword (open-ended)",  "❌ no",       "✅ search tool"),
            ("Ambiguous / multi-intent queries",        "❌ fallback",  "✅ reasons"),
            ("Self-correct after tool error",           "❌ no",       "✅ yes"),
        ]
        for cap, cb, ag in capabilities:
            print(f"  {cap:<42} {cb:^14} {ag:^14}")

        print(f"\n  💬 Chatbot baseline answers (no LLM – pure keyword dispatch):")
        for i, r in enumerate(chatbot_results, 1):
            print(f"\n  [{i}] {r['question']}")
            print(f"       {r['answer'][:160]}{'...' if len(r['answer']) > 160 else ''}")
            print(f"       ({r['elapsed_ms']:.1f} ms)")
    else:
        chatbot_results = []

    # ── Optional report ────────────────────────────────────────────────────
    if args.report:
        report_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "report", "agent_eval_report.md"
        )
        generate_report(
            provider_name=args.provider,
            model_name=llm.model_name,
            agent_results=agent_results,
            chatbot_results=chatbot_results,
            output_path=report_path,
        )

    _hr("═")
    print("  Demo complete. Check logs/ for full JSON traces.")
    _hr("═")


if __name__ == "__main__":
    main()
