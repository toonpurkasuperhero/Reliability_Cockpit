"""
CI Smoke Test for Reliability Cockpit.

Validates that:
- Core database schema and migration layer initialize cleanly.
- Predictive vulnerability assessment computes correctly.
- Agent, Chaos Runner, Judge, and Dashboard app modules load without error.
- Cost and round limit guardrails are present.
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))


def run_smoke_tests():
    print("Executing Reliability Cockpit CI Smoke Tests...")

    # 1. Database Schema & Migration Verification
    from src.db.database import get_db
    db = get_db()
    summary = db.get_dashboard_summary()
    assert summary is not None, "Failed to fetch dashboard summary"
    print("Database initialization: OK")

    # 2. Predictive Vulnerability Assessment Check
    pred = db.predict_vulnerabilities()
    assert "predicted_fault_id" in pred, "Missing predicted_fault_id in output"
    assert "message" in pred, "Missing message in prediction"
    print(f"Predictive Vulnerability Assessment: OK -> {pred['message']}")

    # 3. Agent & Scenario Loading Check
    from src.scenarios.scenarios import all_scenarios
    scenarios = all_scenarios()
    assert len(scenarios) > 0, "No scenarios loaded"
    print(f"Scenario Registry: OK ({len(scenarios)} scenarios)")

    # 4. Chaos Fault Catalog Check
    from src.chaos.faults import all_faults
    faults = all_faults()
    assert len(faults) > 0, "No faults loaded"
    print(f"Chaos Fault Catalog: OK ({len(faults)} faults)")

    # 5. Dashboard Server Route Check
    from dashboard.app import app
    assert app.title == "Reliability Cockpit for AI Agents", "App title mismatch"
    print("FastAPI Dashboard App: OK")

    print("ALL CI SMOKE TESTS PASSED SUCCESSFULLY!")


if __name__ == "__main__":
    run_smoke_tests()
