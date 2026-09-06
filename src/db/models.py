"""
Database schema for the Reliability Cockpit.

All tables are created up front in Phase 0 so that schema migrations
are never needed as we build Phase 1–9 on top of the same store.
"""

# ── Runs ──────────────────────────────────────────────────────────────────────
# One row per agent execution (baseline / chaos / post-mitigation)
CREATE_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS runs (
    id              TEXT PRIMARY KEY,
    scenario_id     TEXT NOT NULL,
    persona_id      TEXT NOT NULL,
    run_type        TEXT NOT NULL DEFAULT 'baseline',
    user_message    TEXT,
    agent_response  TEXT,
    status          TEXT NOT NULL DEFAULT 'running',
    total_input_tokens  INTEGER DEFAULT 0,
    total_output_tokens INTEGER DEFAULT 0,
    total_cost_usd      REAL    DEFAULT 0.0,
    total_latency_ms    REAL    DEFAULT 0.0,
    workflow_json   TEXT,
    agenticlens_report_path TEXT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT
);
"""

# ── Spans ─────────────────────────────────────────────────────────────────────
# One row per AgenticLens step/span within a run
CREATE_SPANS_TABLE = """
CREATE TABLE IF NOT EXISTS spans (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL,
    span_name   TEXT NOT NULL,
    span_type   TEXT,
    input_tokens    INTEGER DEFAULT 0,
    output_tokens   INTEGER DEFAULT 0,
    cost_usd        REAL    DEFAULT 0.0,
    latency_ms      REAL    DEFAULT 0.0,
    input_data      TEXT,
    output_data     TEXT,
    error_message   TEXT,
    caused_by_span_id TEXT,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id),
    FOREIGN KEY (caused_by_span_id) REFERENCES spans(id)
);
"""

# ── Chaos events ──────────────────────────────────────────────────────────────
# One row per agentic-chaos injection event within a run
CREATE_CHAOS_EVENTS_TABLE = """
CREATE TABLE IF NOT EXISTS chaos_events (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL,
    fault_type  TEXT NOT NULL,
    outcome     TEXT NOT NULL,
    step_name   TEXT,
    message     TEXT,
    is_adversarial  INTEGER DEFAULT 0,
    attack_round    INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);
"""

# ── Judge verdicts ────────────────────────────────────────────────────────────
# Structured-state LLM-as-judge result for each run
CREATE_JUDGE_VERDICTS_TABLE = """
CREATE TABLE IF NOT EXISTS judge_verdicts (
    id              TEXT PRIMARY KEY,
    run_id          TEXT NOT NULL,
    passed          INTEGER NOT NULL DEFAULT 0,
    score           REAL    DEFAULT 0.0,
    failure_category TEXT,
    root_cause_step  TEXT,
    reasoning       TEXT NOT NULL,
    expected_state  TEXT,
    actual_state    TEXT,
    created_at      TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);
"""

# ── Mitigations ───────────────────────────────────────────────────────────────
# Auto-mitigation events — maps judge verdict to mitigation strategy
CREATE_MITIGATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS mitigations (
    id          TEXT PRIMARY KEY,
    run_id      TEXT NOT NULL,
    strategy    TEXT NOT NULL,
    result      TEXT NOT NULL,
    explanation TEXT,
    pre_score   REAL,
    post_score  REAL,
    retry_count INTEGER DEFAULT 0,
    created_at  TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);
"""

# ── MTTR records ──────────────────────────────────────────────────────────────
# Mean Time To Recovery tracking — four timestamps per fault
CREATE_MTTR_TABLE = """
CREATE TABLE IF NOT EXISTS mttr_records (
    id                      TEXT PRIMARY KEY,
    run_id                  TEXT NOT NULL,
    fault_type              TEXT NOT NULL,
    fault_injected_at       TEXT,
    detected_at             TEXT,
    mitigation_triggered_at TEXT,
    recovery_confirmed_at   TEXT,
    mttr_seconds            REAL,
    created_at              TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);
"""

ALL_TABLES = [
    CREATE_RUNS_TABLE,
    CREATE_SPANS_TABLE,
    CREATE_CHAOS_EVENTS_TABLE,
    CREATE_JUDGE_VERDICTS_TABLE,
    CREATE_MITIGATIONS_TABLE,
    CREATE_MTTR_TABLE,
]
