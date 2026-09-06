"""
Refund Support Agent — core implementation.

Uses google-generativeai (still functional, just shows FutureWarning)
for function calling. The tool executor is injectable for chaos testing.

Instrumentation dual-path:
  1. agenticlens profile() + step() -> workflow profiler
  2. agenticlens trace() + span.record_tokens() -> Gemini token tracking
"""

from __future__ import annotations

import json
import os
import time
import warnings
from typing import Any, Callable, Dict, List, Optional, Tuple

# Suppress FutureWarning from the old SDK while we still support function calling
with warnings.catch_warnings():
    warnings.simplefilter("ignore", FutureWarning)
    import google.generativeai as genai

from agenticlens import profile, step

from ..agent.tools import ALL_TOOLS, execute_tool
from ..observability.tracer import InstrumentedRun, emit_agenticlens_trace

# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful and professional customer support agent for an e-commerce platform.

Your responsibilities:
1. Look up customer orders using order_lookup when an order ID is mentioned.
2. Process refunds using process_refund only for eligible delivered orders.
3. Provide policy information using policy_lookup when asked about policies.
4. Always check order status and eligibility BEFORE processing a refund.
5. Never fabricate order data, refund amounts, or policy details.
6. If an order is ineligible, explain clearly and empathetically.
7. For orders above Rs. 10000, mention that quality inspection is required.

Be accurate, transparent, and empathetic. Customer trust is paramount."""


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_tokens(response) -> Tuple[int, int]:
    try:
        u = response.usage_metadata
        return (u.prompt_token_count or 0, u.candidates_token_count or 0)
    except (AttributeError, TypeError):
        return 0, 0


def _extract_text(response) -> str:
    try:
        return response.text or ""
    except (AttributeError, ValueError):
        return ""


def _get_function_calls(response) -> List[Any]:
    calls = []
    try:
        for candidate in response.candidates:
            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    calls.append(part.function_call)
    except (AttributeError, IndexError):
        pass
    return calls


def _send_with_retry(chat, payload, max_retries: int = 3, initial_delay: float = 2.5):
    delay = initial_delay
    for attempt in range(max_retries):
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                return chat.send_message(payload)
        except Exception as e:
            if "ResourceExhausted" in type(e).__name__ or "429" in str(e) or "Quota exceeded" in str(e):
                if attempt < max_retries - 1:
                    time.sleep(delay)
                    delay *= 1.5
                    continue
            raise e


# ── Agent ──────────────────────────────────────────────────────────────────────

class RefundSupportAgent:
    """
    Stateless Gemini agent with injectable tool executor.
    The chaos runner replaces _tool_executor with chaos_call() wrappers (Phase 3).
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        tool_executor: Optional[Callable[[str, Dict[str, Any]], str]] = None,
        api_key: Optional[str] = None,
    ) -> None:
        self.model_name = model_name or os.getenv("AGENT_MODEL", "gemini-3.6-flash")
        _key = api_key or os.getenv("GOOGLE_API_KEY")
        if not _key:
            raise ValueError("GOOGLE_API_KEY not set. Copy .env.example -> .env")

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FutureWarning)
            genai.configure(api_key=_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                tools=ALL_TOOLS,
                system_instruction=SYSTEM_PROMPT,
            )

        self._tool_executor: Callable = tool_executor or execute_tool

    def run(
        self,
        user_message: str,
        scenario_id: str = "S00",
        persona_id: str = "P01",
        run_type: str = "baseline",
        run: Optional[InstrumentedRun] = None,
    ) -> Tuple[str, InstrumentedRun]:
        instrumented = run or InstrumentedRun(
            scenario_id=scenario_id,
            persona_id=persona_id,
            run_type=run_type,
            user_message=user_message,
            model=self.model_name,
        )
        with instrumented:
            response_text, wf_json = self._run_loop(user_message, instrumented)
            instrumented.finalize(
                agent_response=response_text,
                status="completed",
                workflow_json=wf_json,
            )
        emit_agenticlens_trace(instrumented)
        return response_text, instrumented

    def _run_loop(
        self, user_message: str, run: InstrumentedRun
    ) -> Tuple[str, Optional[str]]:
        wf_json: Optional[str] = None

        with profile(f"RefundAgent/{run.run_type}/{run.scenario_id}") as wf:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", FutureWarning)
                chat = self.model.start_chat()

            # ── Turn 0: planning call ─────────────────────────────────────────
            t0 = time.perf_counter()
            with step("LLM: Planning", type="planner",
                      provider="google", model=self.model_name, prompt=user_message):
                response = _send_with_retry(chat, user_message)

            in_tok, out_tok = _extract_tokens(response)
            run.record_span(
                name="LLM: Planning", span_type="planner",
                input_tokens=in_tok, output_tokens=out_tok,
                latency_ms=(time.perf_counter() - t0) * 1000,
                input_data=user_message,
            )

            # ── Tool-calling loop ──────────────────────────────────────────────
            tools_called: List[str] = []
            last_fault_span_id: Optional[str] = None
            for turn in range(6):  # cap at 6 turns
                fcs = _get_function_calls(response)
                if not fcs:
                    break

                tool_parts = []
                for fc in fcs:
                    t_tool = time.perf_counter()
                    err = None
                    with step(f"Tool: {fc.name}", type="tool_call"):
                        try:
                            result = self._tool_executor(fc.name, dict(fc.args))
                        except Exception as e:
                            err = str(e)
                            result = json.dumps({"error": err})

                    is_faulty = err is not None or (isinstance(result, str) and ("error" in result.lower() or "chaos" in result.lower()))
                    tool_span_id = run.record_span(
                        name=f"Tool: {fc.name}", span_type="tool_call",
                        latency_ms=(time.perf_counter() - t_tool) * 1000,
                        input_data=dict(fc.args),
                        output_data=result,
                        error_message=err,
                        caused_by_span_id=last_fault_span_id,
                    )
                    if is_faulty and not last_fault_span_id:
                        last_fault_span_id = tool_span_id

                    tools_called.append(fc.name)

                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore", FutureWarning)
                        tool_parts.append(
                            genai.protos.Part(
                                function_response=genai.protos.FunctionResponse(
                                    name=fc.name,
                                    response={"result": result},
                                )
                            )
                        )

                t_resp = time.perf_counter()
                with step(f"LLM: Response turn-{turn+1}", type="final_response",
                          provider="google", model=self.model_name):
                    response = _send_with_retry(chat, tool_parts)

                in2, out2 = _extract_tokens(response)
                run.record_span(
                    name=f"LLM: Response turn-{turn+1}", span_type="final_response",
                    input_tokens=in2, output_tokens=out2,
                    latency_ms=(time.perf_counter() - t_resp) * 1000,
                    output_data=_extract_text(response),
                    caused_by_span_id=last_fault_span_id,
                )

        try:
            wf_json = json.dumps(wf.to_dict() if hasattr(wf, "to_dict") else {})
        except Exception:
            wf_json = None

        return _extract_text(response), wf_json

    def run_scenario(
        self,
        scenario_id: str,
        persona_id: str = "P01",
        user_message: Optional[str] = None,
        custom_user_message: Optional[str] = None,
        run_type: str = "baseline",
        run_id: Optional[str] = None,
    ) -> Tuple[str, InstrumentedRun]:
        import uuid
        from ..scenarios.scenarios import get_scenario
        sc = get_scenario(scenario_id)
        msg = custom_user_message or user_message or sc.user_message
        inst_run = InstrumentedRun(
            run_id=run_id or str(uuid.uuid4()),
            scenario_id=scenario_id,
            persona_id=persona_id,
            run_type=run_type,
            user_message=msg,
            model=self.model_name,
        )
        return self.run(
            user_message=msg,
            scenario_id=scenario_id,
            persona_id=persona_id,
            run_type=run_type,
            run=inst_run,
        )
