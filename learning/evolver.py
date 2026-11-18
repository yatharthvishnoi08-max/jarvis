"""Agent Config & Persona Evolver — auto-tunes system prompts from feedback.
Adapted from OpenJarvis AgentConfigEvolver.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from learning.traces import TraceStore, trace_store
from tools.meta_tools import log_learned_rule

class AgentConfigEvolver:
    """Analyzes negative feedback notes and successful runs to propose prompt enhancements."""

    def __init__(self, store: Optional[TraceStore] = None):
        self.store = store or trace_store

    def analyze_feedback_and_evolve(self) -> Dict[str, Any]:
        """Review recent negative feedback and generate corrective guidance."""
        traces = self.store.list_traces(limit=50)
        negative_feedback = []

        for t_summary in traces:
            trace = self.store.get_trace(t_summary["trace_id"])
            if trace and trace.feedback_score is not None and trace.feedback_score < 0:
                negative_feedback.append({
                    "query": trace.user_query,
                    "response": trace.response_text[:120],
                    "notes": trace.feedback_notes or "User marked as negative"
                })

        if not negative_feedback:
            return {"status": "optimal", "message": "No negative feedback recorded in recent traces."}

        # Formulate lessons learned
        proposed_rules = []
        for nf in negative_feedback[:3]:
            rule_text = f"User correction regarding '{nf['query'][:40]}...': {nf['notes']}"
            proposed_rules.append(rule_text)
            log_learned_rule("feedback_evolution", rule_text)

        return {
            "status": "evolved",
            "negative_cases_analyzed": len(negative_feedback),
            "new_rules_applied": proposed_rules
        }
