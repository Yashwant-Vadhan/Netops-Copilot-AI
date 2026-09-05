import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.db.session as db_session
from app.models.schema import Base
from app.main import app
from app.db.session import get_db
from app.core.config import settings

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    db_file = str(tmp_path / "test_telemetry.db")
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

def test_ingest_telemetry_valid():
    with TestClient(app) as client:
        headers = {"X-Collector-Secret": settings.COLLECTOR_SECRET}
        payload = {
            "interface": "eth0",
            "latency_ms": 25.4,
            "packet_loss_pct": 0.0,
            "throughput_mbps": 100.5
        }
        response = client.post("/api/telemetry/ingest", json=payload, headers=headers)
        assert response.status_code == 201
        data = response.json()
        assert data["error"] is None
        assert data["data"]["interface"] == "eth0"
        assert data["data"]["latency_ms"] == 25.4

def test_ingest_telemetry_missing_secret():
    with TestClient(app) as client:
        payload = {
            "interface": "eth0",
            "latency_ms": 25.4
        }
        response = client.post("/api/telemetry/ingest", json=payload)
        assert response.status_code == 401
        data = response.json()
        assert data["data"] is None
        assert data["error"]["code"] == "UNAUTHORIZED"

def test_ingest_telemetry_missing_metrics():
    with TestClient(app) as client:
        headers = {"X-Collector-Secret": settings.COLLECTOR_SECRET}
        payload = {
            "interface": "eth0"
            # No metrics provided
        }
        response = client.post("/api/telemetry/ingest", json=payload, headers=headers)
        assert response.status_code == 422
        data = response.json()
        assert data["error"]["code"] == "VALIDATION_ERROR"

def test_latest_and_history_telemetry():
    with TestClient(app) as client:
        headers = {"X-Collector-Secret": settings.COLLECTOR_SECRET}
        client.post("/api/telemetry/ingest", json={"interface": "wlan0", "latency_ms": 10.0}, headers=headers)
        client.post("/api/telemetry/ingest", json={"interface": "wlan0", "latency_ms": 45.0}, headers=headers)

        # Test latest
        res_latest = client.get("/api/telemetry/latest?interface=wlan0")
        assert res_latest.status_code == 200
        latest_data = res_latest.json()["data"]
        assert latest_data["latency_ms"] == 45.0

        # Test history
        res_hist = client.get("/api/telemetry/history?interface=wlan0&minutes=60")
        assert res_hist.status_code == 200
        hist_data = res_hist.json()["data"]
        assert len(hist_data) == 2
