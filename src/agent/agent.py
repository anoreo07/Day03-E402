import ast
import inspect
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from src.core.llm_provider import LLMProvider
from src.telemetry.logger import logger
from src.telemetry.metrics import tracker


class ReActAgent:
    """
    Provider-agnostic ReAct agent.

    The agent follows the lab contract:
    Thought -> Action -> Observation, repeated until Final Answer.
    Actions are JSON-first for reliability, with a legacy tool(args) parser
    kept as a fallback for local/smaller models.
    """

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

    def get_system_prompt(self) -> str:
        tool_descriptions = "\n".join(self._format_tool(tool) for tool in self.tools)
        return f"""
You are a careful ReAct shopping assistant for an e-commerce lab.

Available tools:
{tool_descriptions}

Use this exact loop:
Thought: one short reason about what to do next.
Action: {{"tool": "tool_name", "args": {{"arg_name": "value"}}}}

After the system gives you an Observation, decide whether to call another tool
or finish with:
Final Answer: concise answer for the user, including key numbers when relevant.

Rules:
- Use only listed tools.
- Use raw JSON after Action:. Do not wrap JSON in markdown fences.
- Prefer named args matching each tool schema.
- Do not invent prices, stock, tax, discounts, or shipping. Call tools for them.
- Stop once you have enough observations to answer.
""".strip()

    def run(self, user_input: str) -> str:
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

        for step in range(1, self.max_steps + 1):
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

            final_answer = self._extract_final_answer(response_text)
            action, parse_error = self._parse_action(response_text)

            if final_answer and action is None:
                logger.log_event(
                    "AGENT_END",
                    {
                        "status": "success",
                        "steps": step,
                        "answer": final_answer,
                    },
                )
                return final_answer

            if action is None:
                observation = (
                    "ERROR[PARSE_ERROR]: Expected either Final Answer: or "
                    'Action: {"tool": "...", "args": {...}}. '
                    f"{parse_error or ''}".strip()
                )
                logger.log_event(
                    "PARSE_ERROR",
                    {
                        "step": step,
                        "response": response_text,
                        "error": parse_error,
                    },
                )
                transcript = self._append_observation(
                    transcript, response_text, observation
                )
                continue

            action_key = json.dumps(action, sort_keys=True, ensure_ascii=True)
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

    def _execute_tool(self, tool_name: str, args: Any) -> str:
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

    def _parse_action(self, response_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
        action_block = self._extract_action_block(response_text)
        if not action_block:
            return None, "No Action block found."

        cleaned = self._strip_code_fence(action_block)
        parsed_json = self._try_parse_json_action(cleaned)
        if parsed_json is not None:
            return parsed_json, None

        legacy_action = self._try_parse_legacy_action(cleaned)
        if legacy_action is not None:
            return legacy_action, None

        return None, f"Could not parse action: {cleaned}"

    def _extract_action_block(self, response_text: str) -> Optional[str]:
        match = re.search(r"Action:\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        if not match:
            return None
        block = match.group(1).strip()
        block = re.split(
            r"\n\s*(Observation|Thought|Final Answer)\s*:",
            block,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()
        return block

    def _try_parse_json_action(self, action_text: str) -> Optional[Dict[str, Any]]:
        candidates = [action_text]
        json_match = re.search(r"\{.*\}", action_text, re.DOTALL)
        if json_match:
            candidates.append(json_match.group(0))

        for candidate in candidates:
            try:
                payload = json.loads(candidate)
            except json.JSONDecodeError:
                continue

            tool_name = payload.get("tool") or payload.get("name") or payload.get("action")
            args = payload.get("args", payload.get("arguments", payload.get("action_input", {})))
            if isinstance(tool_name, str):
                return {"tool": tool_name, "args": args or {}}
        return None

    def _try_parse_legacy_action(self, action_text: str) -> Optional[Dict[str, Any]]:
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
        try:
            return ast.literal_eval(node)
        except (ValueError, SyntaxError):
            if isinstance(node, ast.Name):
                return node.id
            return ast.unparse(node)

    def _coerce_arguments(self, func: Any, args: Any) -> Any:
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

    def _extract_final_answer(self, response_text: str) -> Optional[str]:
        match = re.search(r"Final Answer:\s*(.*)", response_text, re.DOTALL | re.IGNORECASE)
        return match.group(1).strip() if match else None

    def _append_observation(self, transcript: str, response_text: str, observation: str) -> str:
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
