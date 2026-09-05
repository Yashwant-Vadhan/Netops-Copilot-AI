import os
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.session as db_session
from app.models.schema import Base
from app.models.telemetry import Telemetry
from app.models.incident import Incident, Recommendation
from app.models.human_decision import HumanDecision
from app.main import app
from app.db.session import get_db

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_file = str(tmp_path / "test.db")
    test_engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    db_session.engine = test_engine
    test_session_local = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db_session.SessionLocal = test_session_local

    def override_get_db():
        db = test_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(bind=test_engine)
    yield
    test_engine.dispose()

def test_pipeline_and_incident_lifecycle():
    with TestClient(app) as client:
        base_time = datetime.now(timezone.utc)
        flags = [
            {"metric": "latency_ms", "severity_score": 3.0, "detected_at": base_time.isoformat()},
            {"metric": "packet_loss_pct", "severity_score": 4.0, "detected_at": (base_time + timedelta(seconds=5)).isoformat()}
        ]
        telemetry_context = {
            "latency_ms": 250.0,
            "packet_loss_pct": 15.0,
            "throughput_mbps": 85.0
        }

        # 1. Trigger pipeline
        res_pipeline = client.post("/api/incidents/pipeline", json={
            "flags": flags,
            "telemetry_context": telemetry_context
        })
        assert res_pipeline.status_code == 201
        inc_data = res_pipeline.json()["data"]
        inc_id = inc_data["id"]
        assert inc_data["status"] == "active"
        assert len(inc_data["evidence"]) >= 2
        assert len(inc_data["recommendations"]) == 1

        # 2. Get list of incidents
        res_list = client.get("/api/incidents?status=active")
        assert res_list.status_code == 200
        assert len(res_list.json()["data"]) == 1

        # 3. Get single incident by ID
        res_single = client.get(f"/api/incidents/{inc_id}")
        assert res_single.status_code == 200
        assert res_single.json()["data"]["id"] == inc_id

        # 4. Attempt to resolve WITHOUT human decision (MUST fail with 400)
        res_resolve_fail = client.patch(f"/api/incidents/{inc_id}/status?new_status=resolved")
        assert res_resolve_fail.status_code == 400
        assert res_resolve_fail.json()["error"]["code"] == "HUMAN_DECISION_REQUIRED"

        # 5. Record human decision (Approve)
        res_decision = client.patch(f"/api/incidents/{inc_id}/decision", json={
            "decision": "approve",
            "notes": "Approved rate limiting application."
        })
        assert res_decision.status_code == 200
        dec_data = res_decision.json()["data"]
        assert dec_data["status"] == "acknowledged"
        assert len(dec_data["decisions"]) == 1

        # 6. Attempt to resolve WITH human decision (MUST succeed)
        res_resolve_success = client.patch(f"/api/incidents/{inc_id}/status?new_status=resolved")
        assert res_resolve_success.status_code == 200
        assert res_resolve_success.json()["data"]["status"] == "resolved"


def test_similar_incidents():
    with TestClient(app) as client:
        base_time = datetime.now(timezone.utc)
        flags1 = [{"metric": "packet_loss_pct", "severity_score": 3.0, "detected_at": base_time.isoformat()}]
        flags2 = [{"metric": "packet_loss_pct", "severity_score": 3.5, "detected_at": (base_time + timedelta(seconds=1)).isoformat()}]

        context1 = {"packet_loss_pct": 12.0}
        context2 = {"packet_loss_pct": 14.0}

        # Create two similar incidents
        res1 = client.post("/api/incidents/pipeline", json={"flags": flags1, "telemetry_context": context1})
        res2 = client.post("/api/incidents/pipeline", json={"flags": flags2, "telemetry_context": context2})

        inc1_id = res1.json()["data"]["id"]
        inc2_id = res2.json()["data"]["id"]

        # Query similar incidents for inc1
        res_similar = client.get(f"/api/incidents/{inc1_id}/similar")
        assert res_similar.status_code == 200
        similar_data = res_similar.json()["data"]
        assert len(similar_data) == 1
        assert similar_data[0]["incident"]["id"] == inc2_id
        assert similar_data[0]["similarity_score"] >= 50.0
