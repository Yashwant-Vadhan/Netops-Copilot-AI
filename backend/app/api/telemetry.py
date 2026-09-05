from datetime import datetime, timezone, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, Header, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.session import get_db
from app.models.telemetry import Telemetry
from app.schemas.telemetry import TelemetryIngest, TelemetryResponse
from app.core.config import settings
from app.core.errors import APIException, success_response

router = APIRouter(prefix="/telemetry", tags=["telemetry"])

@router.post("/ingest", status_code=status.HTTP_201_CREATED)
def ingest_telemetry(
    payload: TelemetryIngest,
    x_collector_secret: Optional[str] = Header(None, alias="X-Collector-Secret"),
    db: Session = Depends(get_db)
):
    if not x_collector_secret or x_collector_secret != settings.COLLECTOR_SECRET:
        raise APIException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="UNAUTHORIZED",
            message="Invalid or missing collector secret header"
        )
    
    record = Telemetry(
        timestamp=payload.timestamp or datetime.now(timezone.utc),
        source_id=payload.source_id,
        interface=payload.interface,
        latency_ms=payload.latency_ms,
        packet_loss_pct=payload.packet_loss_pct,
        throughput_mbps=payload.throughput_mbps,
        bytes_sent=payload.bytes_sent,
        bytes_recv=payload.bytes_recv,
        probe_failed=payload.probe_failed
    )
    
    db.add(record)
    db.commit()
    db.refresh(record)

    data = TelemetryResponse.model_validate(record).model_dump(mode="json")
    return success_response(data=data, status_code=status.HTTP_201_CREATED)

@router.get("/latest")
def get_latest_telemetry(
    interface: str = Query(..., description="Interface name (e.g. eth0, wlan0)"),
    db: Session = Depends(get_db)
):
    record = (
        db.query(Telemetry)
        .filter(Telemetry.interface == interface)
        .order_by(desc(Telemetry.timestamp))
        .first()
    )
    data = TelemetryResponse.model_validate(record).model_dump(mode="json") if record else None
    return success_response(data=data)

@router.get("/history")
def get_telemetry_history(
    interface: str = Query(..., description="Interface name"),
    minutes: int = Query(60, ge=1, le=1440, description="Time window in minutes"),
    db: Session = Depends(get_db)
):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    records = (
        db.query(Telemetry)
        .filter(Telemetry.interface == interface, Telemetry.timestamp >= cutoff)
        .order_by(Telemetry.timestamp.asc())
        .all()
    )
    data = [TelemetryResponse.model_validate(r).model_dump(mode="json") for r in records]
    return success_response(data=data)
