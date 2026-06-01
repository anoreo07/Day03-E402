# Individual Report 2: Debugging Case Study

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**:  
  After fixing the `Final Answer` precedence bug, the local ReAct agent still reached `max_steps` in Case 1. The agent successfully collected the required information for the Wireless Earbuds order, including product ID, stock, price, discount, shipping, and tax, but the model never produced a `Final Answer:`. Instead, it used the final allowed step to call another tool (`calc_tax`) and the loop ended with `Max steps reached without Final Answer.`

- **Log Source**:  
  Source file: `logs/2026-06-01.log`

  Relevant trace:

  ```text
  2026-06-01T10:09:03 AGENT_START
  input = I want to buy 2 Wireless Earbuds with coupon SAVE10 and ship to Hanoi...
  max_steps = 8

  Step 1:
  Action: check_stock({"product_id": "wireless_earbuds"})
  Observation: {"available": false, "quantity": 0}

  Step 2:
  Action: search_products({"query": "Wireless Earbuds"})
  Observation: [{"product_id": "P001", "name": "Wireless Earbuds", "price": 49.99, "shipping_weight_kg": 0.05}]

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

- **Diagnosis**:  
  This failure is mainly a local model termination problem, with a smaller agent-design issue.

  The ReAct loop itself executed correctly: it called the LLM, parsed actions, executed tools, appended observations, and logged each step. The parser also recovered from a malformed JSON output at Step 3. However, the local Phi-3 model continued selecting tools instead of recognizing that enough information had been collected.

  The first step where a final answer could have been produced was after Step 8, when the agent had stock, price, discount, shipping, and tax observations. Because Step 8 was already the last allowed step, the agent had no chance to ask the model again for a final response.

  Root causes:

  - **Model limitation**: The local model tends to continue the `Action` pattern even when the task is complete.
  - **Prompt weakness**: The prompt says to stop once enough observations exist, but the completion criterion is not specific enough for the local model.
  - **Agent limitation**: The agent relies entirely on the model to decide when the task is done. It does not independently detect that the required observations already exist.
  - **Tool/spec mismatch**: The model first guessed `wireless_earbuds` instead of searching for the product ID, which wasted one step.

- **Solution**:  
  The confirmed parser bug was already fixed by making `Final Answer:` take precedence over `Action:`. This prevents the agent from ignoring valid final answers.

  For this current issue, the recommended next fix is to add a lightweight completion detector in `src/agent/agent.py` without changing any tool APIs. After each tool observation, the agent should inspect its history. If the user asked for a total and the history already contains product/price, stock, discount, shipping, and tax observations, the agent should produce a final summary instead of spending another LLM step.

  Smallest proposed improvement:

  ```text
  After calc_tax returns:
  - If prior observations include price/discount and shipping,
  - return a final cost summary immediately.
  ```

  Expected effect:

  - Fewer `max_steps` failures.
  - Less dependence on the local model's ability to decide when to stop.
  - Lower latency because the agent avoids unnecessary extra LLM calls.
  - Better robustness without changing the tool APIs or evaluation metrics.
