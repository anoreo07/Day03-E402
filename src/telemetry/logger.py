import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

class IndustryLogger:
    """Structured logger that simulates industry practices.
    Logs to both console and a file in JSONL format.
    Guards against duplicate handlers when re-instantiated.
    """

    _instances: Dict[str, "IndustryLogger"] = {}

    def __new__(cls, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        """Singleton per *name* to prevent handler duplication."""
        if name in cls._instances:
            return cls._instances[name]
        instance = super().__new__(cls)
        cls._instances[name] = instance
        return instance

    def __init__(self, name: str = "AI-Lab-Agent", log_dir: str = "logs"):
        if hasattr(self, "_initialised"):
            return
        self._initialised = True
        self.log_dir = log_dir
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

        os.makedirs(log_dir, exist_ok=True)

        # ── File handler (JSONL) ──────────────────────────────────────
        log_file = os.path.join(
            log_dir, f"{datetime.now().strftime('%Y-%m-%d')}.log"
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        self.logger.addHandler(file_handler)

        # ── Console handler ───────────────────────────────────────────
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        self.logger.addHandler(console_handler)

    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log a structured event as a single JSON line."""
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event_type,
            "data": data,
        }
        self.logger.info(json.dumps(payload, ensure_ascii=False))

    def log_step(
        self,
        step: int,
        thought: Optional[str],
        action: Optional[Dict[str, Any]],
        observation: Optional[str],
        tokens: Optional[Dict[str, int]] = None,
        duration_ms: Optional[int] = None,
    ) -> None:
        """Convenience method to log a full agent step in one call."""
        self.log_event(
            "AGENT_STEP_DETAIL",
            {
                "step": step,
                "thought": thought,
                "action": action,
                "observation": observation,
                "tokens": tokens or {},
                "duration_ms": duration_ms or 0,
            },
        )

    def info(self, msg: str) -> None:
        self.logger.info(msg)

    def error(self, msg: str, exc_info: bool = True) -> None:
        self.logger.error(msg, exc_info=exc_info)

    def flush(self) -> None:
        """Flush all handlers."""
        for handler in self.logger.handlers:
            handler.flush()

# Global logger instance
logger = IndustryLogger()
