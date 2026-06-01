# Individual Report 1: ReAct Agent Termination Failure
# Individual Report 1: ReAct Agent Termination Failure

## I. Technical Contribution (15 Points)

### Modules Implementated

- `src/agent/agent.py`
  - Inspected and traced the full ReAct loop implementation.
  - Identified the termination decision bug where `Action` parsing can override a valid `Final Answer`.
- `src/core/local_provider.py`
  - Inspected the local GGUF provider used by the demo.
  - Confirmed that the local model generates responses step by step through `llama-cpp-python`.
- `demo.py`
  - Inspected the demo runner and confirmed that each test case calls the same `ReActAgent.run()` loop.
- `logs/2026-06-01.log`
  - Used structured logs to diagnose real failure events from the local model run.

### Code Highlights

Key ReAct loop call:

```python
# src/agent/agent.py
result = self.llm.generate(transcript, system_prompt=self.get_system_prompt())
response_text = (result.get("content") or "").strip()
```

Termination decision:

```python
# src/agent/agent.py
final_answer = self._extract_final_answer(response_text)
action, parse_error = self._parse_action(response_text)

if final_answer and action is None:
    return final_answer
```

This means the agent only exits if a `Final Answer:` exists and no parseable `Action:` exists in the same model response.

Related code locations:

- `src/agent/agent.py:77` calls the LLM for each ReAct step.
- `src/agent/agent.py:103` extracts `Final Answer:`.
- `src/agent/agent.py:104` parses `Action:`.
- `src/agent/agent.py:106` exits only when `final_answer and action is None`.
- `src/agent/agent.py:175` logs `MAX_STEPS` if no successful termination happens.
- `src/core/local_provider.py:51` allows up to `1024` generated tokens per local model call.
- `demo.py:113` runs each test case through `agent.run(...)`.
- `demo.py:303` sets the default max steps to `8`.

### Documentation

The ReAct loop works as follows:

1. `demo.py` creates the LLM provider and initializes `ReActAgent`.
2. For each test case, `demo.py` calls `agent.run(question)`.
3. `agent.run()` sends the current transcript to the LLM.
4. The model returns text containing a `Thought`, an `Action`, or a `Final Answer`.
5. If an action is parsed, the agent executes the selected tool.
6. The tool result is appended as an `Observation`.
7. The loop continues until the agent returns a final answer, hits the loop guard, or reaches `max_steps`.

The main implementation issue found is that `Final Answer:` does not immediately terminate the loop if the same response also contains a parseable `Action:`. This allowed the agent to continue after the task had already been answered.

## II. Debugging Case Study (10 Points)

### Problem Description

During the local model demo, the ReAct agent failed to terminate cleanly. The model sometimes generated a valid `Final Answer:` but continued writing another `Action:` afterward. Because the agent parsed the action too, it ignored the final answer and continued the loop.

In one case, the agent had enough information to answer the backpack question, but instead of returning the valid final answer, it parsed another repeated `search_products` action and triggered the loop guard.

### Log Source

Source: `logs/2026-06-01.log`

Relevant snippet:

```text
LLM_RESPONSE step 6:
Final Answer: The Travel Backpack costs USD 69.99 before tax. The tax for Da Nang, Vietnam, is USD 4.9, making the total pre-shipping cost USD 74.89. The standard shipping to Da Nang is USD 9.75, estimated to take 8 days. Therefore, the total cost including shipping is USD 84.64.

Action: {"tool": "search_products", "args": {"query": "backpack"}}

LOOP_GUARD step 6:
action = {"tool": "search_products", "args": {"query": "backpack"}}
answer = "I could not make progress because the same tool call was repeated."
```

Another failure pattern:

```text
LLM_RESPONSE step 2:
Final Answer: I'm sorry, but the wireless earbuds are currently out of stock.

Action: {"tool": "search_products", "args": {"query": "Wireless Earbuds"}}
```

Instead of stopping at `Final Answer:`, the agent continued by executing `search_products`.

### Diagnosis

The failure is caused by a combination of implementation behavior, prompt weakness, and local model limitations.

Confirmed implementation bug:

- `src/agent/agent.py` extracts both `Final Answer:` and `Action:`.
- The success condition only returns if `final_answer` exists and `action is None`.
- Therefore, if the model outputs both, `Action` takes precedence over `Final Answer`.
- This can make the loop continue after the task has already been solved.

Model-related failure:

- The local Phi-3 model did not always follow the strict ReAct format.
- It produced mixed responses containing both final answers and extra actions.
- It also hallucinated product IDs such as `P0_01` and repeated already-used tool calls.

Prompt-related weakness:

- The prompt tells the model how to use `Action` and `Final Answer`, but it does not strongly enforce that the model must output exactly one of them.
- The prompt does not explicitly say: "Never output both `Action:` and `Final Answer:` in the same response."

Severity:

- Critical: `Final Answer:` can be ignored when an `Action:` appears later in the same response.
- Moderate: malformed model output becomes additional observations and consumes extra steps.
- Moderate: repeated or stale actions can continue until the loop guard or `max_steps`.
- Minor: `max_steps` hides the earlier root cause by reporting only "Max steps reached without Final Answer."

### Solution

No code fix has been applied yet in this report. The recommended fix is:

1. In `src/agent/agent.py`, return immediately when `Final Answer:` is detected.
2. Only parse `Action:` when no final answer exists.
3. Optionally tighten the prompt later so the model outputs exactly one of `Action:` or `Final Answer:`.
4. Treat `max_steps` as a safety fallback, not the primary failure explanation.

Estimated root-cause split:

- Code / agent implementation: 40%
- Local model quality: 40%
- Prompt design: 20%

The agent framework is mostly working: it calls the LLM, parses actions, executes tools, appends observations, and logs each step. However, the termination decision is flawed because valid final answers can be skipped when the model also emits an action.
