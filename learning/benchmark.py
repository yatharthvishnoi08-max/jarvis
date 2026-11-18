"""Personal Benchmark Synthesizer — creates evaluation test cases from real user traces.
Adapted from OpenJarvis PersonalBenchmarkSynthesizer.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from learning.traces import TraceStore, trace_store

@dataclass
class BenchmarkCase:
    id: str
    query: str
    expected_response_snippet: str
    category: str
    target_tools: List[str]

class PersonalBenchmarkSynthesizer:
    """Mines user traces to compile a personalized regression evaluation suite."""

    def __init__(self, store: Optional[TraceStore] = None):
        self.store = store or trace_store

    def synthesize(self, max_cases: int = 15) -> List[BenchmarkCase]:
        traces = self.store.list_traces(limit=max_cases * 3)
        cases: List[BenchmarkCase] = []
        seen_queries = set()

        for t_summary in traces:
            trace = self.store.get_trace(t_summary["trace_id"])
            if not trace:
                continue

            query = trace.user_query.strip()
            if not query or query in seen_queries or len(query) < 5:
                continue

            seen_queries.add(query)

            # Categorize
            category = "general_chat"
            tools = [s.tool_name for s in trace.steps]
            if any(t in ("execute_powershell", "write_file", "read_file") for t in tools):
                category = "system_operations"
            elif any(t in ("web_search", "fetch_web_page", "run_deep_research") for t in tools):
                category = "web_research"
            elif any(t in ("calculator", "code_interpreter") for t in tools):
                category = "computation"

            cases.append(BenchmarkCase(
                id=trace.trace_id,
                query=query,
                expected_response_snippet=trace.response_text[:100],
                category=category,
                target_tools=tools
            ))

            if len(cases) >= max_cases:
                break

        return cases
