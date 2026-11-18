"""Training Data Miner — extracts supervised pairs and operational heuristics from traces.
Adapted from OpenJarvis TrainingDataMiner.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from learning.traces import TraceStore, trace_store

class TrainingDataMiner:
    """Mines execution traces to extract successful interaction patterns,
    few-shot exemplars, and behavioral lessons.
    """

    def __init__(self, store: Optional[TraceStore] = None, min_quality: float = 0.5):
        self.store = store or trace_store
        self.min_quality = min_quality

    def mine_exemplars(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Extract high-quality (user_query, response, tools) exemplars from traces."""
        traces_summary = self.store.list_traces(limit=limit * 2)
        exemplars = []

        for summary in traces_summary:
            trace = self.store.get_trace(summary["trace_id"])
            if not trace:
                continue
            
            # Check if trace had positive or neutral feedback with zero tool errors
            has_error = any(step.error for step in trace.steps)
            if has_error:
                continue

            score = trace.feedback_score if trace.feedback_score is not None else 0.0
            if score >= self.min_quality:
                exemplars.append({
                    "query": trace.user_query,
                    "response": trace.response_text,
                    "tools_used": [s.tool_name for s in trace.steps],
                    "score": score
                })
                if len(exemplars) >= limit:
                    break

        return exemplars

    def mine_error_patterns(self) -> List[Dict[str, Any]]:
        """Identify tools and inputs that frequently fail or get rejected."""
        error_stats: Dict[str, int] = {}
        traces_summary = self.store.list_traces(limit=100)

        for summary in traces_summary:
            trace = self.store.get_trace(summary["trace_id"])
            if not trace:
                continue
            for step in trace.steps:
                if step.error:
                    error_stats[step.tool_name] = error_stats.get(step.tool_name, 0) + 1

        return [{"tool": k, "failure_count": v} for k, v in sorted(error_stats.items(), key=lambda x: x[1], reverse=True)]

    def distill_heuristic(self) -> Optional[str]:
        """Summarize top mining insights into a concise lesson for Central Brain."""
        exemplars = self.mine_exemplars(limit=5)
        if not exemplars:
            return None

        tools_count: Dict[str, int] = {}
        for ex in exemplars:
            for t in ex["tools_used"]:
                tools_count[t] = tools_count.get(t, 0) + 1

        top_tools = [k for k, _ in sorted(tools_count.items(), key=lambda x: x[1], reverse=True)[:3]]
        return f"Consistently successful workflows frequently leverage: {', '.join(top_tools)}."
