"""Agent loop guard — detect and prevent degenerate tool-calling loops.
Adapted from OpenJarvis core agent safety mechanisms.
"""
from __future__ import annotations

import hashlib
import json
from collections import deque
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Set, Any

@dataclass
class LoopGuardConfig:
    enabled: bool = True
    max_identical_calls: int = 3       # Max times exact same tool + args can run
    ping_pong_window: int = 6          # Max window to detect A-B-A-B alternating cycles
    warn_before_block: bool = True     # Warn on first threshold breach, block on second

@dataclass
class LoopVerdict:
    blocked: bool = False
    warned: bool = False
    reason: str = ""

class LoopGuard:
    """Monitors agent tool invocations to detect and abort infinite loops,
    repetitive arguments, and cyclic tool-calling patterns.
    """

    def __init__(self, config: Optional[LoopGuardConfig] = None):
        self.config = config or LoopGuardConfig()
        self._call_counts: Dict[str, int] = {}
        self._tool_sequence: deque[tuple[str, str]] = deque(maxlen=self.config.ping_pong_window * 2)
        self._warned_signatures: Set[str] = set()

    def _hash_call(self, tool_name: str, args: Any) -> str:
        serialized = json.dumps({"tool": tool_name, "args": args}, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()

    def check(self, tool_name: str, args: Any) -> LoopVerdict:
        if not self.config.enabled:
            return LoopVerdict(blocked=False)

        call_sig = self._hash_call(tool_name, args)
        count = self._call_counts.get(call_sig, 0) + 1
        self._call_counts[call_sig] = count
        self._tool_sequence.append((tool_name, call_sig))

        # 1. Identical call check
        if count >= self.config.max_identical_calls:
            if self.config.warn_before_block and call_sig not in self._warned_signatures:
                self._warned_signatures.add(call_sig)
                return LoopVerdict(
                    warned=True,
                    reason=f"Repetitive execution detected: '{tool_name}' invoked {count} times with identical parameters."
                )
            return LoopVerdict(
                blocked=True,
                reason=f"LOOP GUARD TRIPPED: Tool '{tool_name}' exceeded maximum repetition limit ({self.config.max_identical_calls} calls)."
            )

        # 2. Detect repeated CALLS, not merely alternating tool names. Typing a
        # document and then a Save As path are different steps, not a stuck loop.
        seq = list(self._tool_sequence)
        if len(seq) >= 4:
            # Check length 2 cycle: A B A B
            if seq[-1] == seq[-3] and seq[-2] == seq[-4] and seq[-1] != seq[-2]:
                cycle_key = f"{seq[-2][1]}:{seq[-1][1]}"
                if cycle_key not in self._warned_signatures:
                    self._warned_signatures.add(cycle_key)
                    return LoopVerdict(
                        warned=True,
                        reason=f"Ping-pong cycle detected between '{seq[-2][0]}' and '{seq[-1][0]}'."
                    )
                return LoopVerdict(
                    blocked=True,
                    reason=f"LOOP GUARD TRIPPED: Detected cycling pattern between '{seq[-2][0]}' and '{seq[-1][0]}'."
                )

        return LoopVerdict(blocked=False)

    def reset(self):
        self._call_counts.clear()
        self._tool_sequence.clear()
        self._warned_signatures.clear()
