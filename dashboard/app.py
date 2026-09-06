"""
Phase 7 — Unified Dashboard API Server.

FastAPI web server providing interactive visualization of:
- Trace timeline & tool call spans (AgenticLens)
- Chaos injection matrix & fault events (Agentic-Chaos)
- LLM-as-Judge verdicts & failure root-causes
- Auto-Mitigation status & MTTR trends
- Reliability Nutrition Label & business impact metrics
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from src.db.database import get_db
from src.agent.agent import RefundSupportAgent
from src.chaos.runner import ChaosRunner
from src.judge.judge import StructuredJudge
from src.mitigation.engine import MitigationEngine
from src.reporting.label import ReliabilityLabelGenerator

app = FastAPI(
    title="Reliability Cockpit for AI Agents",
    description="Observability & Chaos Testing Dashboard (AgenticLens + Agentic-Chaos)",
    version="1.0.0",
)

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

db = get_db()
_agent: Optional[RefundSupportAgent] = None
_chaos_runner: Optional[ChaosRunner] = None
_judge: Optional[StructuredJudge] = None
_mitigation_engine: Optional[MitigationEngine] = None
_label_gen: Optional[ReliabilityLabelGenerator] = None


def get_agent() -> RefundSupportAgent:
    global _agent
    if _agent is None:
        _agent = RefundSupportAgent()
    return _agent


def get_chaos_runner() -> ChaosRunner:
    global _chaos_runner
    if _chaos_runner is None:
        _chaos_runner = ChaosRunner()
    return _chaos_runner


def get_judge() -> StructuredJudge:
    global _judge
    if _judge is None:
        _judge = StructuredJudge()
    return _judge


def get_mitigation_engine() -> MitigationEngine:
    global _mitigation_engine
    if _mitigation_engine is None:
        _mitigation_engine = MitigationEngine()
    return _mitigation_engine


def get_label_gen() -> ReliabilityLabelGenerator:
    global _label_gen
    if _label_gen is None:
        _label_gen = ReliabilityLabelGenerator()
    return _label_gen


# ── Page Routes ───────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")


# ── API Routes ────────────────────────────────────────────────────────────────

@app.get("/api/summary")
def get_summary():
    return db.get_dashboard_summary()


@app.get("/api/runs")
def list_runs(run_type: Optional[str] = None, limit: int = 50):
    return db.list_runs(run_type=run_type, limit=limit)


@app.get("/api/runs/{run_id}")
def get_run_details(run_id: str):
    run = db.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    spans = db.get_spans(run_id)
    chaos_events = db.get_chaos_events(run_id)
    verdict = db.get_verdict(run_id)

    return {
        "run": run,
        "spans": spans,
        "chaos_events": chaos_events,
        "verdict": verdict,
    }


from fastapi import FastAPI, HTTPException, Request, Header, Depends

SECRET_KEY = os.getenv("DASHBOARD_SECRET_KEY", "dev-secret-key-change-in-production")


def verify_api_key(x_api_key: Optional[str] = Header(None), api_key: Optional[str] = None):
    if os.getenv("DASHBOARD_REQUIRE_AUTH", "false").lower() == "true":
        provided = x_api_key or api_key
        if not provided or provided != SECRET_KEY:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing X-API-Key header")
    return True


@app.get("/api/predict")
def get_prediction():
    return db.predict_vulnerabilities()


@app.get("/api/fingerprint")
def get_fingerprint():
    return db.get_fingerprint()


@app.get("/api/label")
def get_label():
    label = get_label_gen().generate_label()
    return label.__dict__


@app.post("/api/trigger/baseline", dependencies=[Depends(verify_api_key)])
def trigger_baseline(scenario_id: str = "S01", persona_id: str = "P01"):
    try:
        response_text, run = get_agent().run_scenario(
            scenario_id=scenario_id,
            persona_id=persona_id,
            run_type="baseline",
        )
        return {"status": "success", "run_id": run.run_id, "response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trigger/chaos", dependencies=[Depends(verify_api_key)])
def trigger_chaos(scenario_id: str = "S01", persona_id: str = "P01", fault_id: str = "F01"):
    try:
        response_text, run, f_id = get_chaos_runner().run_chaos_scenario(
            scenario_id=scenario_id,
            persona_id=persona_id,
            fault_id=fault_id,
        )
        run_id = run.run_id if run else "failed"
        return {"status": "success", "run_id": run_id, "fault_id": f_id, "response": response_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trigger/judge", dependencies=[Depends(verify_api_key)])
def trigger_judge(run_id: Optional[str] = None):
    try:
        if run_id:
            verdict = get_judge().judge_run(run_id)
            return {"status": "success", "verdict": verdict}
        else:
            count = get_judge().judge_all_pending()
            return {"status": "success", "judged_count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/trigger/mitigate", dependencies=[Depends(verify_api_key)])
def trigger_mitigate(run_id: str):
    try:
        res = get_mitigation_engine().mitigate_run(run_id)
        return {"status": "success", "mitigation": res}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
