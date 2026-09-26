"""
Structured logging for e-commerce video CS agent.

Adapted from code-review.md patterns (TypeScript/evlog) to Python:
- Session-scoped logger with context accumulation (wide events)
- Structured errors with message + why + fix + cause
- Single emit per operation instead of scattered log calls
"""

import json
import logging
import traceback
from dataclasses import dataclass, field
from typing import Any


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(name)s] %(levelname)s %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


class SessionLogger:
    """Session-scoped logger that accumulates context and emits wide events.

    Mirrors the useLogger(event) pattern from code-review.md:
        log = SessionLogger("session", room=ctx.room.name)
        log.set(user={"id": customer_id})
        log.set(cart={"items": 3})
        log.info("checkout_completed")  # single wide event with all context
    """

    def __init__(self, name: str, **initial_context: Any) -> None:
        self._logger = get_logger(name)
        self._context: dict[str, Any] = dict(initial_context)

    def set(self, **kwargs: Any) -> None:
        self._context.update(kwargs)

    def info(self, event: str, **extra: Any) -> None:
        self._emit(logging.INFO, event, extra)

    def error(self, event: str, error: BaseException | None = None, **extra: Any) -> None:
        if error:
            extra["error"] = {"type": type(error).__name__, "message": str(error)}
        self._emit(logging.ERROR, event, extra)

    def warning(self, event: str, **extra: Any) -> None:
        self._emit(logging.WARNING, event, extra)

    def debug(self, event: str, **extra: Any) -> None:
        self._emit(logging.DEBUG, event, extra)

    def _emit(self, level: int, event: str, extra: dict[str, Any]) -> None:
        merged = {**self._context, **extra}
        structured = json.dumps(merged, ensure_ascii=False, default=str)
        self._logger.log(level, "[%s] %s", event, structured)

    def child(self, suffix: str) -> "SessionLogger":
        child = SessionLogger(f"{self._logger.name}.{suffix}")
        child._context = dict(self._context)
        return child


@dataclass
class AgentError(Exception):
    """Structured error with message + why + fix + cause.

    Mirrors createError({ message, why, fix, cause }) from code-review.md.
    """

    message: str
    why: str = ""
    fix: str = ""
    step: str = ""
    _cause: BaseException | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        super().__init__(self.message)

    @classmethod
    def wrap(cls, error: BaseException, *, message: str, step: str = "", fix: str = "") -> "AgentError":
        return cls(
            message=message,
            why=str(error),
            fix=fix,
            step=step,
            _cause=error,
        )

    def to_dict(self) -> dict[str, str]:
        result = {"message": self.message}
        if self.why:
            result["why"] = self.why
        if self.fix:
            result["fix"] = self.fix
        if self.step:
            result["step"] = self.step
        return result
