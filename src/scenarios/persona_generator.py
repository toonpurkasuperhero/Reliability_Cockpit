"""
Phase 2 — Persona message generator.

Uses Gemini to rewrite each scenario's user_message through the lens of
each persona. Results are cached in SQLite so subsequent runs are instant.

The generator is intentionally simple — one call per persona×scenario pair.
Token counts are tracked for cost reporting.
"""

from __future__ import annotations

import os
import time
import warnings
from typing import Dict, Optional, Tuple

with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai

from ..agent.personas import Persona, all_personas
from ..scenarios.scenarios import Scenario, all_scenarios

# ── Prompt template ───────────────────────────────────────────────────────────

_GENERATION_PROMPT = """You are simulating a real customer contacting an e-commerce support agent.

ORIGINAL SCENARIO MESSAGE:
{user_message}

PERSONA INSTRUCTION:
{llm_instruction}

Generate EXACTLY ONE message that this persona would send. Follow the persona style precisely.
Return ONLY the message text — no labels, no quotes, no preamble, no explanation.
The message must still convey the same underlying intent as the original."""


def generate_persona_message(
    scenario: Scenario,
    persona: Persona,
    model_name: str = "gemini-3.6-flash",
    api_key: Optional[str] = None,
) -> Tuple[str, int, int]:
    """
    Generate a persona-rewritten version of the scenario message.

    Returns:
        (generated_message, input_tokens, output_tokens)
    """
    _key = api_key or os.getenv("GOOGLE_API_KEY")
    if not _key:
        raise ValueError("GOOGLE_API_KEY not set")

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        genai.configure(api_key=_key)
        model = genai.GenerativeModel(model_name=model_name)

    prompt = _GENERATION_PROMPT.format(
        user_message=scenario.user_message,
        llm_instruction=persona.llm_instruction,
    )

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FutureWarning)
        response = model.generate_content(prompt)

    text = response.text.strip() if response.text else scenario.user_message

    try:
        in_tok = response.usage_metadata.prompt_token_count or 0
        out_tok = response.usage_metadata.candidates_token_count or 0
    except AttributeError:
        in_tok, out_tok = 0, 0

    return text, in_tok, out_tok


def generate_all_persona_messages(
    model_name: str = "gemini-3.6-flash",
    api_key: Optional[str] = None,
) -> Dict[str, Dict[str, str]]:
    """
    Generate persona messages for all persona × scenario combinations.

    Returns:
        {scenario_id: {persona_id: generated_message}}
    """
    result: Dict[str, Dict[str, str]] = {}
    scenarios = all_scenarios()
    personas = all_personas()

    for sc in scenarios:
        result[sc.id] = {}
        for persona in personas:
            if persona.id == "P01":
                # P01 (Polite First-Timer) uses the original message as-is
                result[sc.id][persona.id] = sc.user_message
            else:
                try:
                    msg, _, _ = generate_persona_message(
                        sc, persona, model_name=model_name, api_key=api_key
                    )
                    result[sc.id][persona.id] = msg
                except Exception as e:
                    # Fallback to original on generation failure
                    result[sc.id][persona.id] = sc.user_message

    return result
