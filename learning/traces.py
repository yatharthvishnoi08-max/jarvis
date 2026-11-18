"""Execution trace recording and storage for continuous learning.
Adapted from OpenJarvis TraceStore and trace collection.
"""
from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

BASE_DIR = Path(__file__).resolve().parent.parent
TRACES_DIR = BASE_DIR / "memory" / "traces"

@dataclass
class ToolExecutionStep:
    tool_name: str
    args: Dict[str, Any]
    result: str
    duration_seconds: float
    error: Optional[str] = None

@dataclass
class ExecutionTrace:
    trace_id: str
    session_id: str
    user_query: str
    response_text: str
    timestamp: float
    duration_seconds: float
    model_name: str
    thoughts: List[str] = field(default_factory=list)
    steps: List[ToolExecutionStep] = field(default_factory=list)
    feedback_score: Optional[float] = None  # 1.0 (positive), -1.0 (negative), 0.0 (neutral)
    feedback_notes: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ExecutionTrace:
        steps_data = data.pop("steps", [])
        steps = [ToolExecutionStep(**s) for s in steps_data]
        return cls(steps=steps, **data)


class TraceStore:
    """Persistent storage for agent interaction traces in JSONL and per-trace JSON."""

    def __init__(self, storage_dir: Optional[Path] = None):
        self.storage_dir = storage_dir or TRACES_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.index_file = self.storage_dir / "traces.jsonl"

    def record_trace(self, trace: ExecutionTrace) -> None:
        """Append trace to the index and save full detail file."""
        trace_dict = trace.to_dict()
        
        # Save individual detailed trace file
        trace_path = self.storage_dir / f"{trace.trace_id}.json"
        trace_path.write_text(json.dumps(trace_dict, indent=2), encoding="utf-8")

        # Append summary to index file
        summary = {
            "trace_id": trace.trace_id,
            "session_id": trace.session_id,
            "user_query": trace.user_query[:100],
            "timestamp": trace.timestamp,
            "feedback_score": trace.feedback_score,
            "tools_used": [s.tool_name for s in trace.steps],
            "duration": trace.duration_seconds
        }
        with open(self.index_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(summary) + "\n")

    def update_feedback(self, trace_id: str, score: float, notes: Optional[str] = None) -> bool:
        """Update user feedback score on a stored trace."""
        trace_path = self.storage_dir / f"{trace_id}.json"
        if not trace_path.exists():
            return False

        try:
            data = json.loads(trace_path.read_text(encoding="utf-8"))
            data["feedback_score"] = score
            if notes:
                data["feedback_notes"] = notes
            trace_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            return True
        except Exception:
            return False

    def list_traces(self, limit: int = 50, min_feedback: Optional[float] = None) -> List[Dict[str, Any]]:
        """List recent traces matching criteria."""
        if not self.index_file.exists():
            return []

        results = []
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        item = json.loads(line)
                        if min_feedback is not None:
                            score = item.get("feedback_score")
                            if score is None or score < min_feedback:
                                continue
                        results.append(item)
            return results[-limit:][::-1]
        except Exception:
            return []

    def get_trace(self, trace_id: str) -> Optional[ExecutionTrace]:
        """Load a full trace by ID."""
        trace_path = self.storage_dir / f"{trace_id}.json"
        if not trace_path.exists():
            return None
        try:
            data = json.loads(trace_path.read_text(encoding="utf-8"))
            return ExecutionTrace.from_dict(data)
        except Exception:
            return None

trace_store = TraceStore()
