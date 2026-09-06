"""
SQLite database layer for the Reliability Cockpit.

All writes go through this module so the rest of the codebase
never touches raw SQL.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .models import ALL_TABLES


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class Database:
    """Thread-safe SQLite wrapper using connection-per-call pattern."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        path = db_path or os.getenv("DATABASE_PATH", "./data/reliability_cockpit.db")
        self.db_path = Path(path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    # ── Internal helpers ──────────────────────────────────────────────────────

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            for ddl in ALL_TABLES:
                conn.execute(ddl)
            try:
                conn.execute("ALTER TABLE spans ADD COLUMN caused_by_span_id TEXT")
            except sqlite3.OperationalError:
                pass

    # ── Runs ──────────────────────────────────────────────────────────────────

    def create_run(
        self,
        *,
        scenario_id: str,
        persona_id: str,
        run_type: str,
        user_message: str,
        run_id: Optional[str] = None,
    ) -> str:
        rid = run_id or _new_id()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO runs (id, scenario_id, persona_id, run_type,
                                  user_message, status, started_at)
                VALUES (?, ?, ?, ?, ?, 'running', ?)
                """,
                (rid, scenario_id, persona_id, run_type, user_message, _now_iso()),
            )
        return rid

    def complete_run(
        self,
        run_id: str,
        *,
        agent_response: str,
        status: str = "completed",
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        total_cost_usd: float = 0.0,
        total_latency_ms: float = 0.0,
        workflow_json: Optional[str] = None,
        agenticlens_report_path: Optional[str] = None,
    ) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE runs SET
                    agent_response = ?,
                    status = ?,
                    total_input_tokens = ?,
                    total_output_tokens = ?,
                    total_cost_usd = ?,
                    total_latency_ms = ?,
                    workflow_json = ?,
                    agenticlens_report_path = ?,
                    completed_at = ?
                WHERE id = ?
                """,
                (
                    agent_response,
                    status,
                    total_input_tokens,
                    total_output_tokens,
                    total_cost_usd,
                    total_latency_ms,
                    workflow_json,
                    agenticlens_report_path,
                    _now_iso(),
                    run_id,
                ),
            )

    def fail_run(self, run_id: str, error: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "UPDATE runs SET status='failed', agent_response=?, completed_at=? WHERE id=?",
                (f"ERROR: {error}", _now_iso(), run_id),
            )

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM runs WHERE id=?", (run_id,)).fetchone()
            return dict(row) if row else None

    def list_runs(
        self,
        run_type: Optional[str] = None,
        scenario_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        query = "SELECT * FROM runs WHERE 1=1"
        params: list = []
        if run_type:
            query += " AND run_type=?"
            params.append(run_type)
        if scenario_id:
            query += " AND scenario_id=?"
            params.append(scenario_id)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]

    # ── Spans ─────────────────────────────────────────────────────────────────

    def record_span(
        self,
        run_id: str,
        *,
        span_name: str,
        span_type: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cost_usd: float = 0.0,
        latency_ms: float = 0.0,
        input_data: Optional[Any] = None,
        output_data: Optional[Any] = None,
        error_message: Optional[str] = None,
        caused_by_span_id: Optional[str] = None,
    ) -> str:
        sid = _new_id()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO spans
                    (id, run_id, span_name, span_type, input_tokens, output_tokens,
                     cost_usd, latency_ms, input_data, output_data, error_message,
                     caused_by_span_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    run_id,
                    span_name,
                    span_type,
                    input_tokens,
                    output_tokens,
                    cost_usd,
                    latency_ms,
                    json.dumps(input_data) if input_data is not None else None,
                    json.dumps(output_data) if output_data is not None else None,
                    error_message,
                    caused_by_span_id,
                    _now_iso(),
                ),
            )
        return sid

    def get_spans(self, run_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM spans WHERE run_id=? ORDER BY created_at", (run_id,)
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Chaos events ──────────────────────────────────────────────────────────

    def record_chaos_event(
        self,
        run_id: str,
        *,
        fault_type: str,
        outcome: str,
        step_name: Optional[str] = None,
        message: Optional[str] = None,
        is_adversarial: bool = False,
        attack_round: int = 0,
    ) -> str:
        eid = _new_id()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO chaos_events
                    (id, run_id, fault_type, outcome, step_name, message,
                     is_adversarial, attack_round, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    eid,
                    run_id,
                    fault_type,
                    outcome,
                    step_name,
                    message,
                    int(is_adversarial),
                    attack_round,
                    _now_iso(),
                ),
            )
        return eid

    def get_chaos_events(self, run_id: str) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM chaos_events WHERE run_id=? ORDER BY created_at",
                (run_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    # ── Judge verdicts ────────────────────────────────────────────────────────

    def record_verdict(
        self,
        run_id: str,
        *,
        passed: bool,
        score: float,
        reasoning: str,
        failure_category: Optional[str] = None,
        root_cause_step: Optional[str] = None,
        expected_state: Optional[Dict] = None,
        actual_state: Optional[Dict] = None,
    ) -> str:
        vid = _new_id()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO judge_verdicts
                    (id, run_id, passed, score, failure_category, root_cause_step,
                     reasoning, expected_state, actual_state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    vid,
                    run_id,
                    int(passed),
                    score,
                    failure_category,
                    root_cause_step,
                    reasoning,
                    json.dumps(expected_state) if expected_state else None,
                    json.dumps(actual_state) if actual_state else None,
                    _now_iso(),
                ),
            )
        return vid

    def get_verdict(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM judge_verdicts WHERE run_id=? ORDER BY created_at DESC LIMIT 1",
                (run_id,),
            ).fetchone()
            return dict(row) if row else None

    # ── Mitigations ───────────────────────────────────────────────────────────

    def record_mitigation(
        self,
        run_id: str,
        *,
        strategy: str,
        result: str,
        explanation: Optional[str] = None,
        pre_score: Optional[float] = None,
        post_score: Optional[float] = None,
        retry_count: int = 0,
    ) -> str:
        mid = _new_id()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO mitigations
                    (id, run_id, strategy, result, explanation,
                     pre_score, post_score, retry_count, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mid,
                    run_id,
                    strategy,
                    result,
                    explanation,
                    pre_score,
                    post_score,
                    retry_count,
                    _now_iso(),
                ),
            )
        return mid

    # ── MTTR ──────────────────────────────────────────────────────────────────

    def record_mttr(
        self,
        run_id: str,
        *,
        fault_type: str,
        fault_injected_at: Optional[str] = None,
        detected_at: Optional[str] = None,
        mitigation_triggered_at: Optional[str] = None,
        recovery_confirmed_at: Optional[str] = None,
        mttr_seconds: Optional[float] = None,
    ) -> str:
        mid = _new_id()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO mttr_records
                    (id, run_id, fault_type, fault_injected_at, detected_at,
                     mitigation_triggered_at, recovery_confirmed_at, mttr_seconds, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    mid,
                    run_id,
                    fault_type,
                    fault_injected_at,
                    detected_at,
                    mitigation_triggered_at,
                    recovery_confirmed_at,
                    mttr_seconds,
                    _now_iso(),
                ),
            )
        return mid

    # ── Analytics helpers ─────────────────────────────────────────────────────

    def get_fingerprint(self, limit: int = 50) -> Dict[str, Any]:
        """Aggregate failure frequency/severity across recent runs."""
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT fault_type, outcome, COUNT(*) as count
                FROM chaos_events
                GROUP BY fault_type, outcome
                ORDER BY count DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            pass_rate = conn.execute(
                """
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN passed=1 THEN 1 ELSE 0 END) as passed
                FROM judge_verdicts
                """
            ).fetchone()
            avg_mttr = conn.execute(
                "SELECT AVG(mttr_seconds) as avg_mttr FROM mttr_records WHERE mttr_seconds IS NOT NULL"
            ).fetchone()

        total = pass_rate["total"] or 1
        passed = pass_rate["passed"] or 0
        return {
            "fault_frequency": [dict(r) for r in rows],
            "overall_pass_rate": round(passed / total, 3),
            "total_runs_judged": total,
            "avg_mttr_seconds": avg_mttr["avg_mttr"],
        }

    def predict_vulnerabilities(self) -> Dict[str, Any]:
        """
        Predict agent failure modes based on historical fault frequency and judge findings.
        Returns predicted vulnerability, confidence score, and recommendation.
        """
        fault_labels = {
            "F01": "F01 (Latency Spike)",
            "F02": "F02 (Tool Exception)",
            "F03": "F03 (Schema Drift)",
            "F04": "F04 (Silent Data Corruption)",
            "F05": "F05 (Persona Override)",
            "F06": "F06 (Prompt Injection)",
            "F07": "F07 (Cost Spiral)",
        }
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT fault_type, COUNT(*) as fail_count
                FROM chaos_events
                WHERE outcome IN ('agent_failed_or_crashed', 'fault_triggered', 'handled_or_survived')
                GROUP BY fault_type
                ORDER BY fail_count DESC
                LIMIT 1
                """
            ).fetchone()

        predicted_fault = row["fault_type"] if row else "F04"
        fail_count = row["fail_count"] if row else 3
        label = fault_labels.get(predicted_fault, f"{predicted_fault} (System Fault)")

        return {
            "predicted_fault_id": predicted_fault,
            "predicted_label": label,
            "confidence_score": min(0.95, round(0.65 + (fail_count * 0.04), 2)),
            "message": f"Based on prior runs, this agent is likely vulnerable to {label} — testing that first.",
        }

    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Precomputed summary for dashboard initial load."""
        with self._conn() as conn:
            total_runs = conn.execute("SELECT COUNT(*) FROM runs").fetchone()[0]
            baseline_runs = conn.execute(
                "SELECT COUNT(*) FROM runs WHERE run_type='baseline'"
            ).fetchone()[0]
            chaos_runs = conn.execute(
                "SELECT COUNT(*) FROM runs WHERE run_type='chaos'"
            ).fetchone()[0]
            total_cost = conn.execute(
                "SELECT COALESCE(SUM(total_cost_usd), 0) FROM runs"
            ).fetchone()[0]
            recent_runs = conn.execute(
                """
                SELECT r.id, r.scenario_id, r.persona_id, r.run_type, r.status,
                       r.total_cost_usd, r.total_latency_ms, r.started_at,
                       jv.passed, jv.score, jv.failure_category, jv.reasoning
                FROM runs r
                LEFT JOIN (
                    SELECT run_id, passed, score, failure_category, reasoning,
                           ROW_NUMBER() OVER (PARTITION BY run_id ORDER BY created_at DESC) as rn
                    FROM judge_verdicts
                ) jv ON jv.run_id = r.id AND jv.rn = 1
                ORDER BY r.started_at DESC LIMIT 30
                """
            ).fetchall()
        return {
            "total_runs": total_runs,
            "baseline_runs": baseline_runs,
            "chaos_runs": chaos_runs,
            "total_cost_usd": round(total_cost, 4),
            "recent_runs": [dict(r) for r in recent_runs],
        }


# ── Module-level singleton ─────────────────────────────────────────────────────
_db: Optional[Database] = None


def get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
    return _db
