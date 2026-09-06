"""
Phase 3 — Chaos Fault Catalog using Agentic-Chaos.

Defines both standard Agentic-Chaos faults (TokenTimeout, RateLimitStorm, SilentDegradation, ToolCallFailure, InfiniteLoop)
and domain-specific custom faults (PromptInjection, CostSpiral).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
import random

from agentic_chaos.chaos import (
    TokenTimeoutFault,
    RateLimitStormFault,
    SilentDegradationFault,
)
from agentic_chaos.agents import (
    ToolCallFailureFault,
    InfiniteLoopFault,
)


@dataclass
class FaultDefinition:
    id: str
    name: str
    category: str  # llm, tool, policy, prompt_injection, cost
    description: str
    fault_object: Any  # Agentic-Chaos fault instance or custom handler


FAULT_CATALOG: Dict[str, FaultDefinition] = {
    "F01": FaultDefinition(
        id="F01",
        name="LLM Rate Limit Storm",
        category="llm",
        description="Simulates 429 Rate Limit Storm on Gemini API calls.",
        fault_object=RateLimitStormFault(burst_count=3, retry_after=2.0),
    ),
    "F02": FaultDefinition(
        id="F02",
        name="LLM Token Stream Timeout",
        category="llm",
        description="Simulates token generation timeout mid-response.",
        fault_object=TokenTimeoutFault(hang_seconds=2.0, mode="raise"),
    ),
    "F03": FaultDefinition(
        id="F03",
        name="Tool Payment Gateway Down",
        category="tool",
        description="Simulates process_refund API returning 504 Gateway Timeout.",
        fault_object=ToolCallFailureFault(
            mode="error",
            error_message="504 Gateway Timeout: Payment Provider Unreachable",
        ),
    ),
    "F04": FaultDefinition(
        id="F04",
        name="Tool Silent Data Corruption",
        category="tool",
        description="Simulates process_refund returning $0 refund silently.",
        fault_object=SilentDegradationFault(
            degrade_fn=lambda res: {**res, "refund_amount": 0.0, "status": "processed_zero_amount"} if isinstance(res, dict) else res
        ),
    ),
    "F05": FaultDefinition(
        id="F05",
        name="Tool Infinite Retry Loop",
        category="tool",
        description="Simulates tool call getting stuck in repeated calls.",
        fault_object=InfiniteLoopFault(force_turns=3),
    ),
    "F06": FaultDefinition(
        id="F06",
        name="Prompt Injection Attack",
        category="prompt_injection",
        description="Adversarial payload attempting policy bypass / unauthorized refund.",
        fault_object=None,  # Handled in runner via user message override
    ),
    "F07": FaultDefinition(
        id="F07",
        name="Cost Spiral Trigger",
        category="cost",
        description="Forces repetitive tool queries causing token / cost explosion.",
        fault_object=None,
    ),
}


def get_fault(fault_id: str) -> FaultDefinition:
    if fault_id not in FAULT_CATALOG:
        raise KeyError(f"Unknown fault ID: {fault_id}")
    return FAULT_CATALOG[fault_id]


def all_faults() -> List[FaultDefinition]:
    return list(FAULT_CATALOG.values())
