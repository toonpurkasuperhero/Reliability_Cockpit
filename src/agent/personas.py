"""
5 user personas for the Inclusive Innovation theme.

Each persona represents a realistic, diverse user type.
The persona's system prompt suffix changes how the user message
is phrased without changing the underlying scenario.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass
class Persona:
    id: str
    name: str
    description: str
    message_style: str       # How this persona typically writes
    llm_instruction: str     # Injected into the message-generation prompt


PERSONAS: Dict[str, Persona] = {
    "P01": Persona(
        id="P01",
        name="Polite First-Timer",
        description="A first-time online shopper, polite and slightly uncertain about the process.",
        message_style="Formal, uses full sentences, over-explains, may say 'I hope this is the right place'",
        llm_instruction=(
            "Rewrite the scenario message as a polite first-time online shopper "
            "who is unfamiliar with the refund process. Use formal language, "
            "be slightly hesitant, and over-explain the situation."
        ),
    ),
    "P02": Persona(
        id="P02",
        name="Frustrated Repeat Customer",
        description="An experienced customer who has had issues before and is venting frustration.",
        message_style="Short, terse, uses exclamations, may reference past bad experiences",
        llm_instruction=(
            "Rewrite the scenario message as a frustrated, repeat customer who "
            "has dealt with this company before and is annoyed. Use short sentences, "
            "express irritation, and demand quick resolution."
        ),
    ),
    "P03": Persona(
        id="P03",
        name="Non-Native English Speaker",
        description="A user whose first language is not English — may use simpler grammar, different idioms.",
        message_style="Simple grammar, occasional unusual phrasing, direct requests",
        llm_instruction=(
            "Rewrite the scenario message as someone whose first language is not English. "
            "Use simple grammar, avoid complex idioms, and keep sentences short. "
            "The meaning should be clear but the phrasing slightly non-idiomatic."
        ),
    ),
    "P04": Persona(
        id="P04",
        name="Policy Tester",
        description="A savvy user who knows the system and tries to get more than they're entitled to.",
        message_style="References specific policy clauses, pushes boundaries, asks leading questions",
        llm_instruction=(
            "Rewrite the scenario message as a customer who has read the refund policy "
            "carefully and is trying to maximize their refund, possibly asking for more "
            "than the order value or beyond the return window. The agent should handle this ethically."
        ),
    ),
    "P05": Persona(
        id="P05",
        name="Accessibility Tool User",
        description="A user relying on screen reader / voice input — messages are terse, minimal punctuation.",
        message_style="Very short, minimal punctuation, no caps, functional phrasing only",
        llm_instruction=(
            "Rewrite the scenario message as typed via voice-to-text or a screen reader "
            "input: very short, no punctuation, all lowercase, purely functional. "
            "Example: 'refund order ord 001 damaged earbuds'."
        ),
    ),
}


def get_persona(persona_id: str) -> Persona:
    if persona_id not in PERSONAS:
        raise ValueError(f"Unknown persona: {persona_id}. Valid: {list(PERSONAS.keys())}")
    return PERSONAS[persona_id]


def all_personas() -> List[Persona]:
    return list(PERSONAS.values())
