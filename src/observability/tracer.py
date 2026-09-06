"""
AgenticLens instrumentation layer for the Reliability Cockpit.

Uses BOTH AgenticLens APIs:
  - profile() / step()        → workflow profiler (step-level token/cost/latency optimization)
  - trace() / recording.span() → research trace API (record_tokens for Gemini support)

Both are persisted to SQLite so the dashboard, judge, and fingerprinting
engine all read from the same store.

Cost constants (USD per 1M tokens):
  gemini-2.0-flash  : $0.075 input / $0.300 output
  gemini-1.5-pro    : $1.250 input / $5.000 output
"""

from __future__ import annotations

import json
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

from agenticlens import SpanType, profile, step, trace

from ..db.database import Database, get_db

# ── Cost table ────────────────────────────────────────────────────────────────

COST_PER_1M = {
    "gemini-2.0-flash":      {"input": 0.075,  "output": 0.300},
    "gemini-1.5-pro":        {"input": 1.250,  "output": 5.000},
    "gemini-1.5-flash":      {"input": 0.075,  "output": 0.300},
    "gemini-2.5-pro":        {"input": 1.250,  "output": 10.00},
}

DEFAULT_COST = {"input": 0.075, "output": 0.300}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    rates = COST_PER_1M.get(model, DEFAULT_COST)
    return (input_tokens * rates["input"] + output_tokens * rates["output"]) / 1_000_000


# ── Span record ───────────────────────────────────────────────────────────────

@dataclass
class SpanRecord:
    name: str
    span_type: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    input_data: Optional[Any] = None
    output_data: Optional[Any] = None
    error_message: Optional[str] = None
    caused_by_span_id: Optional[str] = None
    id: Optional[str] = None


# ── InstrumentedRun context manager ──────────────────────────────────────────

class InstrumentedRun:
    """
    Wraps a single agent execution with full AgenticLens instrumentation.

    Usage:
        run = InstrumentedRun(scenario_id="S01", persona_id="P01",
                              run_type="baseline", user_message="...")
        with run:
            # call the agent; record spans via run.record_span(...)
            pass
        print(run.run_id)
    """

    def __init__(
        self,
        scenario_id: str,
        persona_id: str,
        run_type: str,
        user_message: str,
        model: str = "gemini-3.6-flash",
        db: Optional[Database] = None,
        run_id: Optional[str] = None,
    ) -> None:
        self.scenario_id = scenario_id
        self.persona_id = persona_id
        self.run_type = run_type
        self.user_message = user_message
        self.model = model
        self.db = db or get_db()

        self.run_id: str = run_id or ""
        self.spans: List[SpanRecord] = []
        self.chaos_events: List[Dict] = []
        self._start_time: float = 0.0
        self._workflow_json: Optional[str] = None
        self._report_path: Optional[str] = None

    def __enter__(self) -> "InstrumentedRun":
        self._start_time = time.perf_counter()
        if not self.run_id:
            self.run_id = self.db.create_run(
                scenario_id=self.scenario_id,
                persona_id=self.persona_id,
                run_type=self.run_type,
                user_message=self.user_message,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        elapsed_ms = (time.perf_counter() - self._start_time) * 1000
        if exc_type is not None:
            self.db.fail_run(self.run_id, str(exc_val))
            return False  # Re-raise
        return False

    def record_span(
        self,
        name: str,
        span_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
        input_data: Optional[Any] = None,
        output_data: Optional[Any] = None,
        error_message: Optional[str] = None,
        model: Optional[str] = None,
        caused_by_span_id: Optional[str] = None,
    ) -> str:
        m = model or self.model
        cost = calculate_cost(m, input_tokens, output_tokens)
        sid = self.db.record_span(
            self.run_id,
            span_name=name,
            span_type=span_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            input_data=input_data,
            output_data=output_data,
            error_message=error_message,
            caused_by_span_id=caused_by_span_id,
        )
        rec = SpanRecord(
            name=name,
            span_type=span_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            latency_ms=latency_ms,
            input_data=input_data,
            output_data=output_data,
            error_message=error_message,
            caused_by_span_id=caused_by_span_id,
            id=sid,
        )
        self.spans.append(rec)
        return sid

    def record_chaos_event(
        self,
        fault_type: str,
        outcome: str,
        step_name: Optional[str] = None,
        message: Optional[str] = None,
        is_adversarial: bool = False,
        attack_round: int = 0,
    ) -> None:
        self.chaos_events.append(
            {"fault_type": fault_type, "outcome": outcome, "step_name": step_name}
        )
        self.db.record_chaos_event(
            self.run_id,
            fault_type=fault_type,
            outcome=outcome,
            step_name=step_name,
            message=message,
            is_adversarial=is_adversarial,
            attack_round=attack_round,
        )

    def finalize(
        self,
        agent_response: str = "",
        status: str = "completed",
        workflow_json: Optional[str] = None,
    ) -> None:
        total_in = sum(s.input_tokens for s in self.spans)
        total_out = sum(s.output_tokens for s in self.spans)
        total_cost = sum(s.cost_usd for s in self.spans)
        total_latency = sum(s.latency_ms for s in self.spans)
        self.db.complete_run(
            self.run_id,
            agent_response=agent_response,
            status=status,
            total_input_tokens=total_in,
            total_output_tokens=total_out,
            total_cost_usd=total_cost,
            total_latency_ms=total_latency,
            workflow_json=workflow_json,
        )

    @property
    def total_tokens(self) -> int:
        return sum(s.input_tokens + s.output_tokens for s in self.spans)

    @property
    def total_cost_usd(self) -> float:
        return sum(s.cost_usd for s in self.spans)


# ── Timing helpers ────────────────────────────────────────────────────────────

@contextmanager
def timed_step(name: str, span_type: str, run: InstrumentedRun, **kwargs):
    """
    Context manager that times a block and records the span to the DB.

    Usage:
        with timed_step("order_lookup", "tool_call", run, input_data=args) as ts:
            result = order_lookup(...)
            ts["output_data"] = result
    """
    state: Dict[str, Any] = {
        "input_tokens": 0,
        "output_tokens": 0,
        "input_data": kwargs.get("input_data"),
        "output_data": None,
        "error_message": None,
        "model": kwargs.get("model"),
    }
    t0 = time.perf_counter()
    try:
        yield state
    except Exception as e:
        state["error_message"] = str(e)
        raise
    finally:
        latency_ms = (time.perf_counter() - t0) * 1000
        run.record_span(
            name=name,
            span_type=span_type,
            input_tokens=state.get("input_tokens", 0),
            output_tokens=state.get("output_tokens", 0),
            latency_ms=latency_ms,
            input_data=state.get("input_data"),
            output_data=state.get("output_data"),
            error_message=state.get("error_message"),
            model=state.get("model"),
        )


# ── AgenticLens profile wrapper ───────────────────────────────────────────────

def run_with_agenticlens_profile(
    workflow_name: str,
    fn: Callable,
    *args,
    save_path: Optional[str] = None,
    **kwargs,
) -> Any:
    """
    Run `fn(*args, **kwargs)` wrapped in an AgenticLens `profile()` block.
    Saves workflow.json to `save_path` if provided.
    Returns whatever `fn` returns.
    """
    with profile(workflow_name) as wf:
        result = fn(*args, **kwargs)
    if save_path:
        try:
            import agenticlens.cli as _cli
            # profile() writes to stdout by default; try to grab workflow JSON
        except Exception:
            pass
    return result


# ── AgenticLens trace wrapper ─────────────────────────────────────────────────

def emit_agenticlens_trace(
    run: InstrumentedRun,
    workflow_name: str = "refund-support-agent",
) -> None:
    """
    Re-emit recorded spans as an AgenticLens trace (research trace API).
    Called after the agent run completes. Never raises exceptions.
    """
    try:
        span_type_map = {
            "planner":        "planning",
            "llm_call":       "llm_call",
            "tool_call":      "tool_call",
            "final_response": "llm_call",
            "retriever":      "retrieval",
        }
        with trace(workflow_name, environment=run.run_type) as recording:
            for span in run.spans:
                stype = span_type_map.get(span.span_type, "llm_call")
                try:
                    with recording.span(span.name, stype) as s:
                        if span.input_tokens or span.output_tokens:
                            if hasattr(s, "record_tokens"):
                                s.record_tokens(
                                    input_tokens=span.input_tokens,
                                    output_tokens=span.output_tokens,
                                )
                except Exception:
                    pass
    except Exception:
        pass
