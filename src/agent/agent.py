"""Provider-agnostic ReAct agent for the e-commerce lab.

ReAct Flow:

User Question
-> LLM generates Thought + Action
-> Agent parses Action
-> Execute Tool
-> Observation
-> Append to Transcript
-> LLM reasons again from real tool data
-> Final Answer

Khái niệm chính:
- Thought: phần suy luận ngắn để chọn bước tiếp theo.
- Action: lời gọi tool có cấu trúc để lấy dữ liệu thật.
- Observation: kết quả tool, được đưa lại vào transcript để model suy luận tiếp.
- Final Answer: câu trả lời cuối cùng cho người dùng.
- Loop Guard: chặn model lặp tool call vô hạn.
- Parse Guard: chặn local model kẹt trong output sai định dạng.

Khác với chatbot thường, ReAct không trả lời ngay từ trí nhớ của model.
Agent buộc model dùng tool để kiểm chứng giá, tồn kho, thuế, ship và coupon.
Điều này giúp bài lab minh họa vòng Thought -> Action -> Observation rõ ràng.
"""

import ast
import inspect
import json
import re
from typing import List, Dict, Any, Optional, Tuple
from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger

class ReActAgent:
    """
    Provider-agnostic ReAct agent.

    The agent follows the lab contract:
    Thought -> Action -> Observation, repeated until Final Answer.
    Actions are JSON-first for reliability, with a legacy tool(args) parser
    kept as a fallback for local/smaller models.

    Trong bài lab, class này là phần "agent loop": nó không tự biết dữ liệu
    mua hàng, mà điều phối LLM và tools để lấy Observation đáng tin cậy.
    """

    # =========================================================================
    # Initialization
    # =========================================================================

    def __init__(
        self,
        llm: LLMProvider,
        tools: List[Dict[str, Any]],
        max_steps: int = 5,
        agent_version: str = "v2-json-actions",
        verbose: bool = False,
    ):
        self.llm = llm
        self.tools = tools
        self.max_steps = max_steps
        self.agent_version = agent_version
        self.verbose = verbose
        self.history: List[Dict[str, Any]] = []
        self.tool_map = {tool["name"]: tool for tool in tools}

    # =========================================================================
    # Prompt Construction
    # =========================================================================

    def get_system_prompt(self) -> str:
        """Build the system prompt that teaches the LLM the ReAct contract.

        Inputs:
            None directly; uses the registered tool list from the agent.

        Outputs:
            A system prompt containing available tools and response rules.

        ReAct role:
            Đây là "luật chơi" cho model. Prompt cần nói rõ khi nào gọi tool
            và khi nào dừng, vì local models thường dễ sinh thêm Action thừa.
        """
        tool_descriptions = "\n".join(self._format_tool(tool) for tool in self.tools)
        return f"""
        You are an intelligent assistant. You have access to the following tools:
        {tool_descriptions}

Use this exact loop:
Thought: one short reason about what to do next.
Action: {{"tool": "tool_name", "args": {{"arg_name": "value"}}}}

After the system gives you an Observation, decide whether to call another tool
or finish with:
Final Answer: concise answer for the user, including key numbers when relevant.

Rules:
- Use only listed tools.
- Output exactly ONE of Action or Final Answer in each response.
- Never output both Action and Final Answer in the same response.
- If enough information exists, output Final Answer immediately.
- Keep Thought under 20 words.
- Use raw JSON after Action:. Do not wrap JSON in markdown fences.
- Prefer named args matching each tool schema.
- Do not guess product IDs.
- If the product ID is unknown, use search_products first, then use the returned product_id.
- Do not invent prices, stock, tax, discounts, or shipping. Call tools for them.
- Stop once you have enough observations to answer.
""".strip()

    # =========================================================================
    # Main ReAct Loop
    # =========================================================================

    def run(self, user_input: str) -> str:
        """Run the full Thought -> Action -> Observation loop.

        Args:
            user_input: The user's shopping question.

        Returns:
            The final answer string, or a guard/failure message if the loop
            cannot safely finish.

        ReAct role:
            Mỗi vòng gọi LLM một lần, parse Action, chạy tool, rồi đưa
            Observation trở lại transcript. Đây là điểm khác biệt lớn với
            chatbot thường: câu trả lời được xây từ dữ liệu tool thay vì đoán.
        """
        self.history = []
        logger.log_event(
            "AGENT_START",
            {
                "input": user_input,
                "model": self.llm.model_name,
                "version": self.agent_version,
                "max_steps": self.max_steps,
            },
        )

        transcript = f"User: {user_input}"
        repeated_actions: Dict[str, int] = {}
        parse_failures: Dict[str, int] = {}

        for step in range(1, self.max_steps + 1):
            # Mỗi step gửi toàn bộ transcript hiện tại để model thấy được
            # các Observation trước đó và không phải tự tưởng tượng dữ liệu.
            result = self.llm.generate(transcript, system_prompt=self.get_system_prompt())
            response_text = (result.get("content") or "").strip()

            tracker.track_request(
                provider=result.get("provider", "unknown"),
                model=self.llm.model_name,
                usage=result.get("usage", {}),
                latency_ms=result.get("latency_ms", 0),
            )

            thought = self._extract_thought(response_text)
            logger.log_event(
                "LLM_RESPONSE",
                {
                    "step": step,
                    "thought": thought,
                    "response": response_text,
                    "latency_ms": result.get("latency_ms", 0),
                    "usage": result.get("usage", {}),
                },
            )

            if self.verbose:
                print(f"\n===== STEP {step} =====")
                print(response_text)

            # Final Answer phải thắng Action. Nếu model đã giải xong rồi
            # nhưng lỡ sinh thêm Action, agent vẫn nên dừng đúng lúc.
            final_answer = self._extract_final_answer(response_text)
            if final_answer:
                logger.log_event(
                    "AGENT_END",
                    {
                        "status": "success",
                        "steps": step,
                        "answer": final_answer,
                        "termination": "final_answer",
                    },
                )
                return final_answer

            action, parse_error = self._parse_action(response_text)

            if action is None:
                # Local models hay lệch format; parse guard giúp lỗi rõ ràng
                # thay vì đốt hết max_steps trong im lặng.
                parse_key = parse_error or "unknown parse error"
                parse_failures[parse_key] = parse_failures.get(parse_key, 0) + 1
                observation = (
                    f"ERROR[PARSE_ERROR step={step} repeat={parse_failures[parse_key]}]: "
                    "Malformed model output. Expected exactly one of "
                    'Final Answer: ... or Action: {"tool": "...", "args": {...}}. '
                    f"{parse_error or ''}".strip()
                )
                logger.log_event(
                    "PARSE_ERROR",
                    {
                        "step": step,
                        "response": response_text,
                        "error": parse_error,
                        "repeat_count": parse_failures[parse_key],
                    },
                )
                if parse_failures[parse_key] >= 3:
                    answer = (
                        "I could not continue because the model repeatedly produced "
                        "malformed ReAct output."
                    )
                    logger.log_event(
                        "PARSE_GUARD",
                        {"step": step, "error": parse_error, "answer": answer},
                    )
                    logger.log_event(
                        "AGENT_END",
                        {"status": "parse_guard", "steps": step, "answer": answer},
                    )
                    return answer
                transcript = self._append_observation(
                    transcript, response_text, observation
                )
                continue

            # Loop guard dùng fingerprint đã chuẩn hóa để bắt các action
            # tương đương về mặt tool, kể cả khi model thêm arg không dùng.
            action_key = self._action_fingerprint(action)
            repeated_actions[action_key] = repeated_actions.get(action_key, 0) + 1
            if repeated_actions[action_key] > 2:
                answer = (
                    "I could not make progress because the same tool call was "
                    "repeated. Please rephrase the request or check the tool output."
                )
                logger.log_event(
                    "LOOP_GUARD",
                    {"step": step, "action": action, "answer": answer},
                )
                logger.log_event(
                    "AGENT_END",
                    {"status": "loop_guard", "steps": step, "answer": answer},
                )
                return answer

            observation = self._execute_tool(action["tool"], action.get("args", {}))
            self.history.append(
                {
                    "step": step,
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                }
            )
            logger.log_event(
                "AGENT_STEP",
                {
                    "step": step,
                    "thought": thought,
                    "action": action,
                    "observation": observation,
                },
            )
            # Completion detector là "lưới an toàn" cho local model: nếu dữ
            # liệu cần thiết đã có đủ, agent có thể kết thúc thay vì chờ LLM
            # tự nói Final Answer ở bước kế tiếp.
            completion_answer = self._maybe_complete_task(user_input)
            if completion_answer:
                logger.log_event(
                    "COMPLETION_DETECTED",
                    {
                        "step": step,
                        "answer": completion_answer,
                    },
                )
                logger.log_event(
                    "AGENT_END",
                    {
                        "status": "success",
                        "steps": step,
                        "answer": completion_answer,
                        "termination": "completion_detector",
                    },
                )
                return completion_answer
            # Sau mỗi tool call, Observation được đưa lại vào transcript
            # để LLM tiếp tục suy luận dựa trên dữ liệu thật.
            transcript = self._append_observation(transcript, response_text, observation)

        answer = "Max steps reached without Final Answer."
        logger.log_event(
            "MAX_STEPS",
            {"max_steps": self.max_steps, "history": self.history},
        )
        logger.log_event(
            "AGENT_END",
            {"status": "max_steps", "steps": self.max_steps, "answer": answer},
        )
        return answer

    # =========================================================================
    # Tool Execution
    # =========================================================================

    def _execute_tool(self, tool_name: str, args: Any) -> str:
        """Execute one parsed tool call and serialize its result.

        Args:
            tool_name: Name of the tool selected by the LLM.
            args: Parsed JSON/list arguments from the Action block.

        Returns:
            A string Observation. Successful tool results are JSON strings;
            failures are explicit ERROR[...] observations.

        ReAct role:
            Tool execution is where the agent leaves "language only" mode and
            asks deterministic code for facts such as price, stock, and tax.
        """
        tool = self.tool_map.get(tool_name)
        if tool is None:
            observation = f"ERROR[UNKNOWN_TOOL]: Tool '{tool_name}' is not available."
            logger.log_event("UNKNOWN_TOOL", {"tool": tool_name, "args": args})
            return observation

        try:
            func = tool["function"]
            coerced_args = self._coerce_arguments(func, args)
            start_args = self._json_safe(coerced_args)
            result = func(**coerced_args) if isinstance(coerced_args, dict) else func(*coerced_args)
            observation = self._to_observation(result)
            logger.log_event(
                "TOOL_CALL",
                {
                    "tool": tool_name,
                    "args": start_args,
                    "observation": observation,
                },
            )
            return observation
        except Exception as exc:
            observation = f"ERROR[TOOL_ERROR]: {tool_name} failed: {exc}"
            logger.log_event(
                "TOOL_ERROR",
                {
                    "tool": tool_name,
                    "args": self._json_safe(args),
                    "error": str(exc),
                },
            )
            return observation

    # =========================================================================
    # Loop Protection
    # =========================================================================

    def _action_fingerprint(self, action: Dict[str, Any]) -> str:
        """Create a normalized key for repeated-action detection.

        Args:
            action: Parsed action payload with tool name and args.

        Returns:
            Stable JSON string used by the loop guard.

        ReAct role:
            Model output can vary slightly between repeated calls. Normalizing
            args through the tool signature keeps harmless extra args from
            bypassing loop protection.
        """
        tool_name = action.get("tool")
        args = action.get("args", {})
        tool = self.tool_map.get(tool_name)

        if tool is not None:
            try:
                args = self._coerce_arguments(tool["function"], args)
            except Exception:
                pass

        return json.dumps(
            {"tool": tool_name, "args": args},
            sort_keys=True,
            ensure_ascii=True,
        )

    # =========================================================================
    # Completion Detection
    # =========================================================================

    def _maybe_complete_task(self, user_input: str) -> Optional[str]:
        """Detect whether accumulated observations are enough to answer.

        Args:
            user_input: Original user question, used to infer required facts.

        Returns:
            A deterministic final answer when the task is complete; otherwise
            None so the ReAct loop can continue.

        ReAct role:
            Local models sometimes keep calling tools after all facts exist.
            This detector adds a conservative agent-side stop condition without
            changing tool APIs.
        """
        requirements = self._completion_requirements(user_input)
        state = self._collect_completion_state()

        if not state.get("product") and requirements["product"]:
            return None

        if requirements["stock"]:
            stock = state.get("stock")
            if not stock:
                return None
            if stock.get("available") is False:
                return self._build_completion_answer(state)

        if requirements["price"] and not state.get("price"):
            return None
        if requirements["discount"] and not state.get("discount"):
            return None
        if requirements["shipping"] and not state.get("shipping"):
            return None
        if requirements["tax"] and not state.get("tax"):
            return None

        return self._build_completion_answer(state)

    def _completion_requirements(self, user_input: str) -> Dict[str, bool]:
        """Infer the minimum observations needed for the user's request.

        Các rule này cố ý đơn giản để phù hợp bài lab: nhận diện từ khóa
        chính như buy, coupon, shipping, tax, total thay vì xây planner lớn.
        """
        text = user_input.lower()
        wants_stock = any(
            marker in text
            for marker in ("buy", "purchase", "order", "stock", "available", "in stock")
        )
        wants_discount = "coupon" in text or "discount" in text
        wants_shipping = any(
            marker in text
            for marker in ("ship", "shipping", "deliver", "hanoi", "ho chi minh", "da nang")
        )
        wants_tax = any(marker in text for marker in ("tax", "total", "cost", "breakdown"))
        wants_price = any(marker in text for marker in ("price", "total", "cost", "buy", "purchase", "order"))

        return {
            "product": True,
            "stock": wants_stock,
            "price": wants_price or wants_discount or wants_tax,
            "discount": wants_discount,
            "shipping": wants_shipping,
            "tax": wants_tax,
        }

    def _collect_completion_state(self) -> Dict[str, Any]:
        """Summarize tool observations into a compact completion state.

        Returns:
            A dictionary containing latest product, stock, price, discount,
            shipping, and tax observations when available.

        ReAct role:
            History lưu từng bước chi tiết; completion state gom các dữ kiện
            cần thiết để biết agent đã đủ thông tin trả lời hay chưa.
        """
        state: Dict[str, Any] = {
            "product": None,
            "stock": None,
            "price": None,
            "discount": None,
            "shipping": None,
            "tax": None,
        }
        stock_by_product: Dict[str, Dict[str, Any]] = {}
        price_by_product: Dict[str, Dict[str, Any]] = {}
        selected_product_id = None

        for item in self.history:
            action = item.get("action", {})
            tool = action.get("tool")
            args = action.get("args", {}) if isinstance(action.get("args", {}), dict) else {}
            observation = self._parse_observation(item.get("observation"))

            if tool == "search_products" and isinstance(observation, list) and observation:
                product = observation[0]
                if isinstance(product, dict) and product.get("product_id"):
                    state["product"] = product
                    selected_product_id = product.get("product_id")
                    if product.get("price") is not None:
                        price_by_product[selected_product_id] = {
                            "product_id": selected_product_id,
                            "price": product.get("price"),
                            "currency": "USD",
                        }

            elif tool == "check_stock" and isinstance(observation, dict):
                product_id = args.get("product_id")
                if product_id:
                    stock_by_product[product_id] = {
                        "product_id": product_id,
                        **observation,
                    }

            elif tool == "get_price" and isinstance(observation, dict):
                product_id = args.get("product_id")
                if product_id and float(observation.get("price", 0) or 0) > 0:
                    price_by_product[product_id] = {
                        "product_id": product_id,
                        **observation,
                    }
                    if not selected_product_id:
                        selected_product_id = product_id
                        state["product"] = {"product_id": product_id}

            elif tool == "get_discount" and isinstance(observation, dict):
                state["discount"] = {
                    "product_id": args.get("product_id"),
                    "base_price": args.get("base_price"),
                    "coupon_code": args.get("coupon_code"),
                    **observation,
                }

            elif tool == "calc_shipping" and isinstance(observation, dict):
                state["shipping"] = {"args": args, **observation}

            elif tool == "calc_tax" and isinstance(observation, dict):
                state["tax"] = {"args": args, **observation}

        if selected_product_id:
            state["stock"] = stock_by_product.get(selected_product_id)
            state["price"] = price_by_product.get(selected_product_id)
        else:
            state["stock"] = next(reversed(stock_by_product.values()), None)
            state["price"] = next(reversed(price_by_product.values()), None)

        return state

    # =========================================================================
    # Observation Handling
    # =========================================================================

    def _parse_observation(self, observation: Any) -> Any:
        """Decode a JSON Observation when possible.

        Tool results are stored as strings in history for logging/transcript
        consistency. Completion detection needs structured values, so this
        helper converts JSON observations back to Python objects.
        """
        if not isinstance(observation, str):
            return observation
        try:
            return json.loads(observation)
        except json.JSONDecodeError:
            return observation

    def _build_completion_answer(self, state: Dict[str, Any]) -> str:
        """Build a deterministic answer from collected observations.

        Args:
            state: Compact facts produced by `_collect_completion_state`.

        Returns:
            A concise final answer grounded only in tool observations.

        ReAct role:
            Đây là fallback an toàn khi tool data đã đủ nhưng local model chưa
            tự kết thúc bằng Final Answer.
        """
        product = state.get("product") or {}
        stock = state.get("stock") or {}
        price = state.get("price") or {}
        discount = state.get("discount") or {}
        shipping = state.get("shipping") or {}
        tax = state.get("tax") or {}

        product_name = product.get("name") or "The product"
        product_id = product.get("product_id") or price.get("product_id") or discount.get("product_id")

        parts = []
        if product_id:
            parts.append(f"{product_name} ({product_id})")
        else:
            parts.append(product_name)

        if stock:
            availability = "in stock" if stock.get("available") else "not in stock"
            quantity = stock.get("quantity")
            stock_text = f"is {availability}"
            if quantity is not None:
                stock_text += f" with {quantity} available"
            parts.append(stock_text)

        if price:
            parts.append(f"unit price ${float(price.get('price', 0.0)):.2f}")

        if discount:
            discount_amount = float(discount.get("discount_amount", 0.0) or 0.0)
            final_price = float(discount.get("final_price", 0.0) or 0.0)
            coupon = discount.get("applied_coupon") or discount.get("coupon_code") or "no coupon"
            parts.append(
                f"discount {coupon}: -${discount_amount:.2f}, discounted subtotal ${final_price:.2f}"
            )

        if shipping:
            parts.append(
                f"shipping ${float(shipping.get('cost', 0.0)):.2f}"
                f" ({shipping.get('estimated_days')} days)"
            )

        if tax:
            parts.append(
                f"tax ${float(tax.get('tax', 0.0)):.2f}"
            )

        final_total = self._estimate_final_total(state)
        if final_total is not None:
            parts.append(f"estimated final total ${final_total:.2f}")

        return "Based on the collected tool observations: " + "; ".join(parts) + "."

    def _estimate_final_total(self, state: Dict[str, Any]) -> Optional[float]:
        """Estimate the final total from discount, tax, and shipping facts.

        The method avoids new tool calls; it only combines existing
        observations so evaluation behavior and tool APIs stay unchanged.
        """
        price = state.get("price") or {}
        discount = state.get("discount") or {}
        shipping = state.get("shipping") or {}
        tax = state.get("tax") or {}

        subtotal = (
            float(discount["final_price"])
            if discount.get("final_price") is not None
            else float(price["price"])
            if price.get("price") is not None
            else None
        )
        shipping_cost = float(shipping.get("cost", 0.0) or 0.0)

        if tax.get("total") is not None:
            tax_total = float(tax["total"])
            tax_args = tax.get("args", {})
            tax_subtotal = tax_args.get("subtotal") if isinstance(tax_args, dict) else None
            if subtotal is not None and tax_subtotal is not None:
                try:
                    tax_subtotal = float(tax_subtotal)
                    if abs(tax_subtotal - subtotal) <= 0.02:
                        return round(tax_total + shipping_cost, 2)
                except (TypeError, ValueError):
                    pass
            return round(tax_total + shipping_cost, 2) if shipping else round(tax_total, 2)

        if subtotal is not None:
            return round(subtotal + shipping_cost, 2)
        return None

    # =========================================================================
    # Utility Functions
    # =========================================================================

    def _format_tool(self, tool: Dict[str, Any]) -> str:
        schema = tool.get("args_schema")
        if not schema:
            schema = self._schema_from_signature(tool["function"])
        return f"- {tool['name']}: {tool['description']} Args: {schema}"

    def _schema_from_signature(self, func: Any) -> Dict[str, str]:
        schema = {}
        for name, param in inspect.signature(func).parameters.items():
            if param.kind in (param.VAR_POSITIONAL, param.VAR_KEYWORD):
                continue
            annotation = param.annotation
            if annotation is inspect._empty:
                type_name = "any"
            elif hasattr(annotation, "__name__"):
                type_name = annotation.__name__
            else:
                type_name = str(annotation)
            schema[name] = type_name
        return schema

    # =========================================================================
    # Action Parsing
    # =========================================================================

    def _parse_action(self, response_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        """Parse the current LLM output into one tool Action.

        Args:
            response_text: Raw text generated by the LLM for this step.

        Returns:
            `(action, None)` when parsing succeeds, or `(None, error)` when
            no valid action exists.

        ReAct role:
            Local models may emit markdown, multiline JSON, or multiple
            candidate actions. The parser prefers the last valid action before
            any Final Answer so stale echoed content is less likely to run.
        """
        action_blocks = self._extract_action_blocks(
            self._text_before_final_answer(response_text)
        )
        if not action_blocks:
            return None, "No Action block found."

        parse_errors = []
        for action_block in reversed(action_blocks):
            cleaned = self._strip_code_fence(action_block)
            parsed_json = self._try_parse_json_action(cleaned)
            if parsed_json is not None:
                return parsed_json, None

            legacy_action = self._try_parse_legacy_action(cleaned)
            if legacy_action is not None:
                return legacy_action, None

            parse_errors.append(f"Could not parse action: {cleaned}")

        return None, "; ".join(parse_errors)

    def _text_before_final_answer(self, response_text: str) -> str:
        """Ignore Action text after Final Answer to preserve termination."""
        match = re.search(r"Final Answer\s*:", response_text, re.IGNORECASE)
        return response_text[: match.start()] if match else response_text

    def _extract_action_blocks(self, response_text: str) -> List[str]:
        """Extract candidate Action blocks from the current model output."""
        action_matches = list(
            re.finditer(r"Action\s*:\s*", response_text, re.IGNORECASE)
        )
        blocks = []
        stop_pattern = re.compile(
            r"\n\s*(?:Action|Observation|Thought|Final Answer|Assistant|User)\s*:",
            re.IGNORECASE,
        )

        for index, match in enumerate(action_matches):
            start = match.end()
            next_action_start = (
                action_matches[index + 1].start()
                if index + 1 < len(action_matches)
                else len(response_text)
            )
            block = response_text[start:next_action_start]
            stop = stop_pattern.search(block)
            if stop:
                block = block[: stop.start()]
            block = block.strip()
            if block:
                blocks.append(block)
        return blocks

    def _try_parse_json_action(self, action_text: str) -> Optional[Dict[str, Any]]:
        """Parse JSON-style actions, including local-model partial wrappers."""
        decoder = json.JSONDecoder()
        candidates = [action_text.strip()]
        candidates.extend(
            action_text[index:].strip()
            for index, char in enumerate(action_text)
            if char == "{"
        )

        for candidate in candidates:
            try:
                payload, _ = decoder.raw_decode(candidate)
            except json.JSONDecodeError:
                continue

            if not isinstance(payload, dict):
                continue
            tool_name = payload.get("tool") or payload.get("name") or payload.get("action")
            args = payload.get("args", payload.get("arguments", payload.get("action_input", {})))
            if isinstance(tool_name, str):
                return {"tool": tool_name, "args": args or {}}
        return None

    def _try_parse_legacy_action(self, action_text: str) -> Optional[Dict[str, Any]]:
        """Parse legacy `tool(arg=...)` actions for smaller local models."""
        match = re.match(r"(?P<tool>[A-Za-z_][A-Za-z0-9_]*)\((?P<args>.*)\)\s*$", action_text, re.DOTALL)
        if not match:
            return None

        tool_name = match.group("tool")
        raw_args = match.group("args").strip()
        if not raw_args:
            return {"tool": tool_name, "args": {}}

        try:
            call = ast.parse(f"_tool({raw_args})", mode="eval").body
            if not isinstance(call, ast.Call):
                return None
            keyword_args = {
                kw.arg: self._literal_or_name(kw.value)
                for kw in call.keywords
                if kw.arg is not None
            }
            if keyword_args:
                return {"tool": tool_name, "args": keyword_args}
            return {
                "tool": tool_name,
                "args": [self._literal_or_name(arg) for arg in call.args],
            }
        except SyntaxError:
            parts = [part.strip().strip("\"'") for part in raw_args.split(",")]
            return {"tool": tool_name, "args": parts}

    def _literal_or_name(self, node: ast.AST) -> Any:
        """Convert AST nodes from legacy action syntax into Python values."""
        try:
            return ast.literal_eval(node)
        except (ValueError, SyntaxError):
            if isinstance(node, ast.Name):
                return node.id
            return ast.unparse(node)

    def _coerce_arguments(self, func: Any, args: Any) -> Any:
        """Coerce model-provided args toward the selected tool signature."""
        signature = inspect.signature(func)
        params = list(signature.parameters.values())

        if isinstance(args, dict):
            coerced: Dict[str, Any] = {}
            accepts_kwargs = any(p.kind == p.VAR_KEYWORD for p in params)
            param_map = {p.name: p for p in params}
            for name, value in args.items():
                if name in param_map:
                    coerced[name] = self._coerce_value(value, param_map[name].annotation)
                elif accepts_kwargs:
                    coerced[name] = value
            return coerced

        if isinstance(args, list):
            coerced_list = []
            positional_params = [
                p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
            ]
            for index, value in enumerate(args):
                annotation = (
                    positional_params[index].annotation
                    if index < len(positional_params)
                    else inspect._empty
                )
                coerced_list.append(self._coerce_value(value, annotation))
            return coerced_list

        return [args]

    def _coerce_value(self, value: Any, annotation: Any) -> Any:
        """Apply lightweight type coercion for common tool argument types."""
        if annotation is inspect._empty or value is None:
            return value
        if annotation is bool and isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes"}
        if annotation in {int, float, str}:
            try:
                return annotation(value)
            except (TypeError, ValueError):
                return value
        return value

    def _extract_thought(self, response_text: str) -> Optional[str]:
        match = re.search(r"Thought:\s*(.*?)(?:\n\s*Action:|\n\s*Final Answer:|$)", response_text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    # =========================================================================
    # Final Answer Detection
    # =========================================================================

    def _extract_final_answer(self, response_text: str) -> Optional[str]:
        """Extract the final user-facing answer from model output.

        Args:
            response_text: Raw model response for the current step.

        Returns:
            The final answer text, or None if no `Final Answer:` marker exists.

        ReAct role:
            Final Answer là điều kiện dừng chính. Phần sau marker này được
            cắt bớt để tránh local model lỡ echo thêm Action hoặc transcript.
        """
        match = re.search(r"Final Answer:\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        answer = match.group(1).strip()
        answer = re.split(
            r"\n\s*(?:Action|Observation|Thought|Assistant|User)\s*:",
            answer,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        answer = re.split(r"\n\s*---\s*(?:\n|$)", answer, maxsplit=1)[0].strip()
        return answer or None

    def _append_observation(self, transcript: str, response_text: str, observation: str) -> str:
        """Append model output and tool Observation to the transcript.

        Args:
            transcript: Current conversation state sent to the LLM.
            response_text: The model's latest Thought/Action text.
            observation: Serialized tool result or parse/tool error.

        Returns:
            Updated transcript for the next ReAct step.

        ReAct role:
            Observation là feedback loop: model nhìn thấy kết quả thật của
            tool và dùng nó để chọn bước tiếp theo hoặc kết luận.
        """
        return f"{transcript}\nAssistant:\n{response_text}\nObservation: {observation}"

    def _strip_code_fence(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        return text.strip()

    def _to_observation(self, result: Any) -> str:
        if isinstance(result, str):
            return result
        return json.dumps(result, ensure_ascii=False, sort_keys=True)

    def _json_safe(self, value: Any) -> Any:
        try:
            json.dumps(value)
            return value
        except TypeError:
            return str(value)
