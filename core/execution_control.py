"""Expose a turn's cooperative stop signal inside its synchronous tool worker."""
from contextvars import ContextVar


_cancelled = ContextVar("tool_cancelled", default=lambda: False)


def cancellation_requested():
    return bool(_cancelled.get()())


def run_tool(fn, args, cancelled):
    # Set this in the executor thread: run_in_executor does not copy contextvars.
    token = _cancelled.set(cancelled)
    try:
        if cancellation_requested():
            return "ERROR: Operation cancelled before tool execution."
        return fn(**args)
    finally:
        _cancelled.reset(token)
