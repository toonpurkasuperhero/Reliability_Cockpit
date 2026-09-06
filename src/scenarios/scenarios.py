"""
5 canonical happy-path scenarios for the Refund Support Agent.

Each scenario defines:
- The user message (what the customer says)
- The expected end state (what the agent MUST produce to pass the judge)
- The tools that MUST be called
- The tools that must NOT be called (over-calling catches hallucination)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class Scenario:
    id: str
    name: str
    user_message: str
    expected_end_state: Dict
    must_call_tools: List[str]
    must_not_call_tools: List[str] = field(default_factory=list)
    description: str = ""


SCENARIOS: Dict[str, Scenario] = {
    "S01": Scenario(
        id="S01",
        name="Standard Refund — Eligible Order",
        description="Customer wants a refund on a recently delivered, refund-eligible order.",
        user_message=(
            "Hi, I received my order ORD-001 last week and I'd like to return it "
            "and get a refund. The earbuds have a defect."
        ),
        expected_end_state={
            "refund_initiated": True,
            "order_id_mentioned": "ORD-001",
            "refund_amount_mentioned": True,
            "user_informed_of_timeline": True,
            "fabricated_data": False,
        },
        must_call_tools=["order_lookup", "process_refund"],
    ),
    "S02": Scenario(
        id="S02",
        name="Policy Inquiry — No Refund Needed",
        description="Customer asks about the refund policy without wanting a refund.",
        user_message=(
            "What's your return policy? How many days do I have to return something?"
        ),
        expected_end_state={
            "policy_explained": True,
            "return_window_mentioned": True,
            "refund_initiated": False,
            "fabricated_data": False,
        },
        must_call_tools=["policy_lookup"],
        must_not_call_tools=["process_refund"],
    ),
    "S03": Scenario(
        id="S03",
        name="Order Status Check — Still Processing",
        description="Customer checks status of an order still in processing — refund ineligible.",
        user_message=(
            "Can you tell me the status of my order ORD-003? It's been a few days."
        ),
        expected_end_state={
            "order_status_communicated": True,
            "order_id_mentioned": "ORD-003",
            "refund_initiated": False,
            "user_told_order_is_processing": True,
            "fabricated_data": False,
        },
        must_call_tools=["order_lookup"],
        must_not_call_tools=["process_refund"],
    ),
    "S04": Scenario(
        id="S04",
        name="Refund for Returned Order — Already Returned",
        description="Customer wants refund status on an already-returned order.",
        user_message=(
            "I returned my USB cable (order ORD-005) about a week ago. "
            "When will I get my refund?"
        ),
        expected_end_state={
            "order_status_communicated": True,
            "order_id_mentioned": "ORD-005",
            "return_status_confirmed": True,
            "refund_timeline_communicated": True,
            "fabricated_data": False,
        },
        must_call_tools=["order_lookup"],
    ),
    "S05": Scenario(
        id="S05",
        name="High-Value Order Refund — Eligibility Check",
        description="Customer wants refund on a high-value order; agent must verify eligibility before processing.",
        user_message=(
            "I want to return my laptop bag, order ORD-004. It arrived damaged. "
            "The bag was ₹12,999. Please process the full refund."
        ),
        expected_end_state={
            "refund_initiated": True,
            "order_id_mentioned": "ORD-004",
            "refund_amount_mentioned": True,
            "eligibility_checked": True,
            "user_informed_of_timeline": True,
            "fabricated_data": False,
        },
        must_call_tools=["order_lookup", "process_refund"],
    ),
}


def get_scenario(scenario_id: str) -> Scenario:
    if scenario_id not in SCENARIOS:
        raise ValueError(f"Unknown scenario: {scenario_id}. Valid: {list(SCENARIOS.keys())}")
    return SCENARIOS[scenario_id]


def all_scenarios() -> List[Scenario]:
    return list(SCENARIOS.values())
