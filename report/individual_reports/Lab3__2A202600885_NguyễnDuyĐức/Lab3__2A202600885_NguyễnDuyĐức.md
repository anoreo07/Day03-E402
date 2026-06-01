# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Duy Đức
- **Student ID**: 2A202600885
- **Date**: 2026-06-01

---

## I. Technical Contribution

### Modules Implemented

My technical contribution focused on strengthening the ReAct agent from a fragile v1 loop into a v2 implementation that could complete multi-step e-commerce tasks using tool evidence, provider abstraction, telemetry, and evaluation traces. The work centered on the agent loop in `src/agent/agent.py`, the tool wrapper layer in `src/tools/__init__.py`, the provider switcher in `src/core/provider_factory.py`, and the evaluation workflow in `demo.py` and `agent_eval_report.md`.

| Module / Tool / Test Area | Contribution | Technical Rationale | Impact on v1 -> v2 Improvements |
|---|---|---|---|
| ReAct Loop: `src/agent/agent.py` | Contributed to the ReAct control loop that coordinates `Thought`, `Action`, `Observation`, and `Final Answer` across multiple tool calls. | The agent must not answer directly from model memory; it needs a repeatable loop that gathers product, stock, price, discount, shipping, and tax evidence before responding. | Supported dynamic multi-step reasoning instead of the baseline chatbot's hardcoded keyword pipeline. This allowed v2 to solve TC-A1, TC-A2, and TC-A3 with real tool observations. |
| Parser / Final Answer Handling: `src/agent/agent.py` | Debugged and improved the handling of mixed model output where `Final Answer:` and `Action:` appeared in the same local-model response. | In v1, a valid final answer could be ignored when a parseable action appeared later in the same response. `Final Answer:` needed to act as the stronger stop signal. | Addressed the v1 failure where the agent continued after already producing an answer, including the backpack case where a final answer was followed by another `search_products` action. |
| Completion Detection Logic: `src/agent/agent.py` | Analyzed the `max_steps` failure pattern and contributed to the v2 completion-detector behavior that summarizes from collected observations when enough evidence exists. | The local Phi-3 model sometimes kept calling tools after stock, price, discount, shipping, and tax had already been collected. The agent needed a conservative stop condition independent of the model's next token choice. | Converted the TC-A1 Wireless Earbuds trace from `Max steps reached without Final Answer` into a successful final response based on collected observations. |
| Tool Wrapper Layer: `src/tools/__init__.py` | Contributed to the wrapper interface for `check_stock_tool`, `get_price_tool`, `get_discount_tool`, `calc_shipping`, `calc_tax`, and `get_ecommerce_tools()`. | Raw business functions require product tables, inventory data, coupon data, or structured parameters. Wrappers pre-bind shared context and expose simpler callable signatures to the LLM. | Reduced tool-call complexity for the model and made the tool registry clearer, more maintainable, and easier to pass into `ReActAgent`. |
| `search_products` Bridge: `src/tools/__init__.py` | Added and validated `search_products(query)` as the bridge from natural product names or categories to concrete product IDs such as `P001` and `P004`. | The local model initially guessed invalid IDs such as `wireless_earbuds`. A search tool was needed so the agent could recover from natural-language product names before calling stock or price tools. | Improved open-ended search behavior in v2. TC-A3 succeeded by finding the backpack product, then pricing it with tax and shipping. |
| Provider Switcher: `src/core/provider_factory.py` | Contributed to the provider switcher through `build_provider_from_env()` and `build_provider()`, supporting `local`, `openai`, and `gemini/google` provider paths. | The agent loop should depend on the `LLMProvider` interface rather than a specific model backend. This lets the same agent run with a local GGUF model or hosted providers. | Made experimentation cleaner: v1/v2 behavior could be evaluated with the local `Phi-3-mini-4k-instruct-q4.gguf` model while keeping the architecture ready for stronger hosted models. |
| Evaluation Framework: `demo.py`, `agent_eval_report.md` | Evaluated the ReAct agent on TC-A1, TC-A2, and TC-A3, capturing status, step count, token usage, latency, and final answers. | The lab scoring requires evidence, not only implementation claims. The demo runner provides measurable outputs for correctness, efficiency, and trace quality. | Demonstrated v2 success on all representative cases: 3/3 pass rate, 4.7 average steps per case, 4303 average tokens per case, and 20047 ms average latency per step. |
| Telemetry Analysis: `logs/2026-06-01.log`, `src/telemetry/logger.py`, `src/telemetry/metrics.py` | Analyzed structured traces to diagnose repeated actions, malformed or mixed outputs, invalid product guesses, tool observations, token usage, and step-level latency. | Without telemetry, `max_steps` would hide the real cause. Step traces showed whether the problem came from tools, parsing, prompting, local-model behavior, or completion logic. | Turned v1 failures into concrete v2 fixes: final-answer precedence, stronger prompt rules, JSON-first action parsing with fallback handling, and completion detection. |

The work evolved across three evidence sources:

- **Before release v1 (`indi_report1.md`)**: The agent could execute tools and append observations, but the control flow was fragile. The main issue was that mixed model output containing both `Final Answer:` and `Action:` could cause the agent to execute the action instead of stopping.
- **Before release v2 (`indi_report2.md`)**: Final-answer precedence was addressed, but a new failure appeared: the local model still reached `max_steps` after collecting enough evidence. This motivated the completion-detector behavior.
- **After v2 evaluation (`agent_eval_report.md`)**: The agent passed 3/3 representative cases with telemetry showing steps, tokens, latency, and final answers.

### Architecture Contributions

A key architecture contribution was separating the LLM-facing tool interface from the raw business functions. The raw functions such as `check_stock`, `get_price`, and `get_discount` depend on product, inventory, and coupon data. The LLM should not call those raw functions directly because it would have to know internal data structures and hidden context arguments. The wrapper layer solves this by exposing small, stable functions such as `check_stock_tool(product_id)` and `get_price_tool(product_id)` while binding the required product database or inventory internally.

This abstraction improves code quality because the agent only needs a registry of tool names, descriptions, and callable functions from `get_ecommerce_tools()`. The ReAct loop can remain focused on reasoning, parsing, tool execution, and observation handling instead of knowing the implementation details of every commerce function.

I also contributed to the provider switcher architecture. `build_provider_from_env()` and `build_provider()` separate agent logic from model backend selection. The same `ReActAgent` can run with the local GGUF provider, OpenAI, or Gemini/Google through a shared `LLMProvider` interface. This makes the system easier to test and maintain because model changes do not require rewriting the ReAct loop or tool layer.

This separation was especially important for the lab because the local Phi-3 model exposed realistic failure modes: malformed JSON, repeated actions, guessed product IDs, and weak stopping behavior. The architecture allowed those failures to be analyzed as agent-loop and provider-behavior issues rather than mixing them into the commerce tools themselves.

### Testing and Evaluation Contributions

The evaluation work used TC-A1, TC-A2, and TC-A3 as evidence for v2 behavior:

| Test Case | Purpose | v2 Result | Evidence Collected |
|---|---|---:|---|
| TC-A1 | Stock check + coupon + tax + shipping to Hanoi for Wireless Earbuds | SUCCESS | 8 steps, 8198 tokens, 18972 ms average latency; final answer included stock, unit price, discount, shipping, tax, and estimated final total. |
| TC-A2 | Invalid coupon + tax + shipping to Ho Chi Minh for Gaming Keyboards | SUCCESS | 3 steps, 2566 tokens, 29452 ms average latency; final answer included coupon handling, tax, shipping, and cost breakdown. |
| TC-A3 | Open-ended backpack search + price + tax + shipping to Da Nang | SUCCESS | 3 steps, 2145 tokens, 11716 ms average latency; final answer used `search_products` to identify Travel Backpack `P004` before calculating final cost. |

The telemetry traces were used to compare v1 and v2 behavior. In v1, the agent could collect useful observations but still fail because the model generated both `Final Answer:` and `Action:` or because it reached `max_steps` after the final useful tool call. The Wireless Earbuds case showed this clearly: the agent collected product ID, stock, price, discount, shipping, and tax, but ended with `Max steps reached without Final Answer.`

The v2 improvements directly addressed those observed failures. Final-answer precedence prevented valid answers from being skipped. Stronger action-format rules reduced mixed output. The `search_products` bridge reduced invalid product-ID guesses. Completion detection allowed the agent to stop once observations already satisfied the user's request. The final evaluation report showed the result with a 3/3 pass rate across the representative ReAct cases.

---

## II. Debugging Case Study 

### Problem Description

The main failure I analyzed was a termination failure in the local ReAct agent. The agent could collect enough information to answer a user query, but it sometimes failed to stop cleanly.

There were two related failure modes:

- The model generated both `Final Answer:` and `Action:` in one response. The agent parsed the action and continued instead of returning the final answer.
- After the final-answer precedence issue was addressed, the local model still sometimes reached `max_steps` because it kept selecting tools instead of recognizing that all required observations had already been collected.

The most important case was the Wireless Earbuds order:

```text
I want to buy 2 Wireless Earbuds with coupon SAVE10 and ship to Hanoi.
Is it in stock and what is the total?
```

The agent collected product ID, stock, price, discount, shipping, and tax, but before the completion improvement it ended with:

```text
Max steps reached without Final Answer.
```

### Log Source

Source: `logs/2026-06-01.log`

Failure trace before the completion improvement:

```text
2026-06-01T10:09:03 AGENT_START
input = I want to buy 2 Wireless Earbuds with coupon SAVE10 and ship to Hanoi...
max_steps = 8

Step 1:
Action: check_stock({"product_id": "wireless_earbuds"})
Observation: {"available": false, "quantity": 0}

Step 2:
Action: search_products({"query": "Wireless Earbuds"})
Observation: [{"product_id": "P001", "name": "Wireless Earbuds", "price": 49.99}]

Step 4:
Action: check_stock({"product_id": "P001"})
Observation: {"available": true, "quantity": 120}

Step 5:
Action: get_price({"product_id": "P001"})
Observation: {"currency": "USD", "price": 49.99}

Step 6:
Action: get_discount({"product_id": "P001", "base_price": 49.99, "coupon_code": "SAVE10"})
Observation: {"applied_coupon": "SAVE10", "discount_amount": 5.0, "final_price": 44.99}

Step 7:
Action: calc_shipping({"weight_kg": 0.05, "destination": {"country": "VN"}, "method": "standard"})
Observation: {"cost": 7.65, "currency": "USD", "estimated_days": 8}

Step 8:
Action: calc_tax({"subtotal": 44.99, "region": "VN"})
Observation: {"rate": 0.07, "tax": 3.15, "total": 48.14}

AGENT_END:
status = max_steps
answer = Max steps reached without Final Answer.
```

Improved trace after adding completion behavior:

```text
2026-06-01T10:35:21 COMPLETION_DETECTED
answer = Based on the collected tool observations: Wireless Earbuds (P001);
is in stock with 120 available; unit price $49.99; discount SAVE10: -$5.00,
discounted subtotal $44.99; shipping $7.65 (8 days); tax $3.15;
estimated final total $55.79.

AGENT_END:
status = success
termination = completion_detector
```

### Diagnosis

The failure was not caused by the tools themselves. The tools returned useful observations, and the telemetry showed that the agent collected the necessary facts. The problem was the control logic around model output and stopping conditions.

Root causes:

- **Agent implementation**: `Final Answer:` was not strong enough as a stop signal when an `Action:` appeared later in the same generated text.
- **Local model behavior**: `Phi-3-mini-4k-instruct-q4.gguf` often continued the action pattern even after enough evidence existed.
- **Prompt weakness**: The prompt needed stronger rules such as "output exactly one of Action or Final Answer" and "never output both."
- **Step budget issue**: In the Wireless Earbuds case, `calc_tax` happened on step 8, so the agent had no remaining LLM step to ask for a final response.
- **Tool/spec mismatch**: The model first guessed `wireless_earbuds` as a product ID before searching for the real ID `P001`, which wasted a step.

The log made the diagnosis clear because it showed every intermediate observation. Without telemetry, the final message "Max steps reached" would hide the real cause.

### Solution

The fix strategy had three parts:

1. Give `Final Answer:` priority over `Action:` so a valid final answer cannot be skipped.
2. Strengthen the system prompt to require exactly one output type per step: either `Action` or `Final Answer`, never both.
3. Add or recommend an agent-side completion detector for cases where tool observations already satisfy the user request.

The final evaluation report shows the result:

| Test Case | Description | Status | Steps | Tokens | Avg Latency |
|---|---|---:|---:|---:|---:|
| TC-A1 | Stock + coupon + tax + shipping to Hanoi | SUCCESS | 8 | 8198 | 18972 ms |
| TC-A2 | Invalid coupon + tax + shipping to Ho Chi Minh | SUCCESS | 3 | 2566 | 29452 ms |
| TC-A3 | Search backpack + price + tax + shipping to Da Nang | SUCCESS | 3 | 2145 | 11716 ms |

Overall pass rate: **3/3 (100%)**. Average steps per case: **4.7**. Average tokens per case: **4303**. Average latency per step: **20047 ms**.

---

## III. Personal Insights: Chatbot vs ReAct

### 1. Reasoning

The `Thought` block makes the agent more inspectable than a normal chatbot. A baseline chatbot can give a fluent answer immediately, but it is hard to know whether the answer came from real data or from pattern matching. In the ReAct agent, each `Thought` explains the next intended step, each `Action` selects a tool, and each `Observation` gives external evidence.

For commerce questions, this is a big difference. A question such as "buy 2 earbuds with coupon and shipping" needs product search, stock check, discount, shipping, and tax. A direct chatbot answer can sound confident while inventing prices or totals. A ReAct trace forces the model to ground the answer in tool outputs.

### 2. Reliability

The agent is not always better. For simple keyword-style questions, the baseline chatbot is faster and more predictable because it can use a hardcoded pipeline without LLM latency. In the evaluation report, the baseline chatbot answered comparable fixed product-ID questions in under 1 ms because it did not need model calls.

The ReAct agent performed worse when the local model produced malformed JSON, repeated stale actions, guessed product IDs, or forgot to stop. This means an agent needs more engineering around parsing, telemetry, loop guards, and completion detection. The reasoning loop is powerful, but it also creates more failure surfaces.

### 3. Observation

The most valuable part of ReAct is the observation feedback loop. When the agent called `search_products("Wireless Earbuds")`, the observation returned the real product ID `P001`. That corrected the earlier bad guess `wireless_earbuds`. When the agent called `get_discount`, the observation gave the exact discount amount and final price. The final answer could then cite real numbers instead of approximate language.

My main insight is that ReAct is not simply "LLM plus tools." It is a controlled protocol for deciding when the model is allowed to speak and when it must first gather evidence. The protocol only works well when the system has strict output parsing, clear stopping rules, and logs detailed enough to explain failures.

---

## IV. Future Improvements 

- **Scalability**: Move tool execution to an asynchronous design so independent calls such as price, stock, shipping, and tax can run faster when dependencies allow it. For a larger system, use a queue-based worker model and cache stable product facts such as price or shipping weight.

- **Safety**: Add a supervisor layer that checks every proposed action before execution. The supervisor should reject unknown tools, impossible product IDs, repeated actions, and suspicious arguments. For production commerce, also add user confirmation before payment or irreversible operations.

- **Performance**: Use a stronger model for planning and a cheaper/local model for formatting, or route simple product-ID questions to the baseline pipeline. Add a vector database for product search so open-ended queries such as "find a backpack" are handled semantically instead of only by keyword matching.

- **Reliability**: Keep the completion detector, loop guard, parse guard, and structured telemetry as first-class parts of the agent. Add automated tests for malformed JSON, mixed `Final Answer` plus `Action`, repeated tool calls, invalid coupon recovery, and max-step termination.

- **Production RAG / Multi-Agent Direction**: Split the system into specialized agents: a product-search agent, pricing agent, logistics agent, and final-answer agent. A coordinator can combine their outputs into one answer while telemetry tracks each sub-agent separately. For RAG, product documentation, policy pages, coupon rules, and shipping rules should be indexed and cited in the final response.

---

## Evidence Summary

- Individual source notes: `indi_report1.md`, `indi_report2.md`, `agent_eval_report.md`
- Group source report: `report/group_report/Lab3_GroupReport.md`
- Rubric source: `SCORING.md`
- Main modules inspected: `src/agent/agent.py`, `src/core/local_provider.py`, `demo.py`
- Telemetry evidence: `logs/2026-06-01.log`
