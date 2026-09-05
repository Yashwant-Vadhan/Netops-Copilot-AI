from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, BigInteger
from app.db.session import Base

class Telemetry(Base):
    __tablename__ = "telemetry"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True, nullable=False)
    source_id = Column(String(100), nullable=False, default="default-collector")
    interface = Column(String(100), nullable=False, index=True)
    latency_ms = Column(Float, nullable=True)
    packet_loss_pct = Column(Float, nullable=True)
    throughput_mbps = Column(Float, nullable=True)
    bytes_sent = Column(BigInteger, nullable=True, default=0)
    bytes_recv = Column(BigInteger, nullable=True, default=0)
    probe_failed = Column(Boolean, nullable=False, default=False)
