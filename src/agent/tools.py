"""
Mock tools for the Refund Support Agent.

All data is realistic and static — no real payment gateway needed.
The chaos runner will wrap these with `chaos_call()` / `wrap_tool()`
during resilience testing (Phase 3).

Each function has a docstring + type hints so Gemini can auto-generate
the function schema from them.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

# ── Mock data store ─────────────────────────────────────────────────────────

ORDERS: Dict[str, Dict[str, Any]] = {
    "ORD-001": {
        "order_id": "ORD-001",
        "customer_name": "Priya Sharma",
        "customer_email": "priya.s@example.com",
        "product": "Noise-Cancelling Wireless Earbuds",
        "amount_inr": 2499.00,
        "status": "delivered",
        "delivery_date": "2026-08-28",
        "order_date": "2026-08-22",
        "refund_eligible": True,
        "refund_window_days": 30,
    },
    "ORD-002": {
        "order_id": "ORD-002",
        "customer_name": "Rahul Verma",
        "customer_email": "rahul.v@example.com",
        "product": "Smart Watch Series 5",
        "amount_inr": 5999.00,
        "status": "delivered",
        "delivery_date": "2026-08-30",
        "order_date": "2026-08-25",
        "refund_eligible": True,
        "refund_window_days": 30,
    },
    "ORD-003": {
        "order_id": "ORD-003",
        "customer_name": "Anita Patel",
        "customer_email": "anita.p@example.com",
        "product": "Premium Phone Case",
        "amount_inr": 899.00,
        "status": "processing",
        "delivery_date": None,
        "order_date": "2026-09-01",
        "refund_eligible": False,
        "refund_window_days": 30,
        "note": "Cannot refund while processing. Will be eligible after delivery.",
    },
    "ORD-004": {
        "order_id": "ORD-004",
        "customer_name": "Mohammed Ali",
        "customer_email": "m.ali@example.com",
        "product": "Premium Laptop Bag (15.6 inch)",
        "amount_inr": 12999.00,
        "status": "delivered",
        "delivery_date": "2026-08-25",
        "order_date": "2026-08-20",
        "refund_eligible": True,
        "refund_window_days": 30,
    },
    "ORD-005": {
        "order_id": "ORD-005",
        "customer_name": "Sarah Kim",
        "customer_email": "sarah.k@example.com",
        "product": "Braided USB-C Cable (2m)",
        "amount_inr": 349.00,
        "status": "returned",
        "delivery_date": "2026-08-27",
        "return_date": "2026-08-30",
        "order_date": "2026-08-21",
        "refund_eligible": True,
        "refund_status": "refund_processing",
        "refund_eta": "2026-09-06",
        "refund_window_days": 30,
    },
}

POLICIES: Dict[str, str] = {
    "refund": """
REFUND POLICY — Effective September 2026

1. RETURN WINDOW: Items can be returned within 30 days of delivery.
2. CONDITION: Items must be in original, undamaged condition with all accessories.
3. ELIGIBILITY: Only 'delivered' orders are eligible for refunds. Processing orders cannot be refunded until delivered.
4. DAMAGED ITEMS: Items damaged during transit are eligible for immediate refund or replacement.
5. PROCESSING TIME: Refunds are processed within 5–7 business days after the returned item is received.
6. REFUND METHOD: Refund is credited to the original payment method (card/wallet/UPI).
7. HIGH-VALUE ORDERS: Orders above ₹10,000 require a quality inspection before refund approval (2–3 business days).
""",
    "shipping": """
SHIPPING POLICY — Effective September 2026

1. Standard delivery: 3–5 business days.
2. Express delivery: 1–2 business days (additional charge).
3. Free shipping on orders above ₹499.
4. No shipping to P.O. boxes.
""",
    "warranty": """
WARRANTY POLICY — Effective September 2026

1. Electronics: 1-year manufacturer warranty.
2. Accessories: 6-month warranty.
3. Warranty does not cover physical damage or water damage.
4. Contact manufacturer directly for warranty claims after 30-day return window.
""",
}

# Simulated refund ledger (in-memory, resets each run)
_REFUND_LEDGER: Dict[str, Dict[str, Any]] = {}


# ── Tool functions ────────────────────────────────────────────────────────────

def order_lookup(order_id: str) -> str:
    """
    Look up an order by its ID and return full order details.

    Args:
        order_id: The order ID to look up (e.g. 'ORD-001').

    Returns:
        JSON string with order details including status, amount, and refund eligibility.
    """
    order = ORDERS.get(order_id.upper())
    if not order:
        return json.dumps({
            "error": f"Order '{order_id}' not found. Please verify the order ID.",
            "found": False,
        })
    return json.dumps({**order, "found": True})


def process_refund(order_id: str, amount_inr: float, reason: str) -> str:
    """
    Process a refund for an eligible order.

    Args:
        order_id: The order ID to refund (e.g. 'ORD-001').
        amount_inr: The refund amount in Indian Rupees.
        reason: The reason for the refund (e.g. 'defective product', 'damaged in transit').

    Returns:
        JSON string with refund confirmation details including reference number and timeline.
    """
    order = ORDERS.get(order_id.upper())

    if not order:
        return json.dumps({
            "success": False,
            "error": f"Order '{order_id}' not found.",
        })

    if not order.get("refund_eligible", False):
        return json.dumps({
            "success": False,
            "error": f"Order '{order_id}' is not eligible for a refund. Status: {order['status']}.",
        })

    if amount_inr > order["amount_inr"]:
        return json.dumps({
            "success": False,
            "error": f"Refund amount ₹{amount_inr:.2f} exceeds order value ₹{order['amount_inr']:.2f}.",
        })

    # High-value inspection check
    inspection_required = order["amount_inr"] > 10000
    refund_ref = f"REF-{order_id}-{abs(hash(reason)) % 100000:05d}"

    _REFUND_LEDGER[refund_ref] = {
        "order_id": order_id,
        "amount_inr": amount_inr,
        "reason": reason,
        "status": "initiated",
    }

    return json.dumps({
        "success": True,
        "refund_reference": refund_ref,
        "order_id": order_id,
        "amount_inr": amount_inr,
        "reason": reason,
        "status": "refund_initiated",
        "inspection_required": inspection_required,
        "processing_days": "7–10 business days" if inspection_required else "5–7 business days",
        "credited_to": "original payment method",
        "message": (
            f"Refund of ₹{amount_inr:.2f} initiated for order {order_id}. "
            f"{'Quality inspection required (2–3 days). ' if inspection_required else ''}"
            f"Funds will be credited within "
            f"{'7–10' if inspection_required else '5–7'} business days."
        ),
    })


def policy_lookup(policy_type: str) -> str:
    """
    Look up a customer support policy.

    Args:
        policy_type: The type of policy to retrieve. Valid values: 'refund', 'shipping', 'warranty'.

    Returns:
        The full text of the requested policy.
    """
    normalized = policy_type.lower().strip()
    policy = POLICIES.get(normalized)
    if not policy:
        available = list(POLICIES.keys())
        return (
            f"Policy '{policy_type}' not found. "
            f"Available policies: {', '.join(available)}."
        )
    return policy.strip()


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOL_REGISTRY: Dict[str, Any] = {
    "order_lookup": order_lookup,
    "process_refund": process_refund,
    "policy_lookup": policy_lookup,
}

ALL_TOOLS = [order_lookup, process_refund, policy_lookup]


def execute_tool(tool_name: str, tool_args: Dict[str, Any]) -> str:
    """Execute a tool by name with the given arguments."""
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        return json.dumps({"error": f"Unknown tool: '{tool_name}'"})
    try:
        return fn(**tool_args)
    except TypeError as e:
        return json.dumps({"error": f"Tool call failed: {str(e)}"})
