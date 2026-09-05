from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict, model_validator

class TelemetryIngest(BaseModel):
    timestamp: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_id: str = Field(default="default-collector")
    interface: str = Field(..., min_length=1)
    latency_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    throughput_mbps: Optional[float] = None
    bytes_sent: Optional[int] = 0
    bytes_recv: Optional[int] = 0
    probe_failed: bool = False

    @model_validator(mode="after")
    def validate_metrics_present(self):
        if not self.probe_failed and self.latency_ms is None and self.packet_loss_pct is None and self.throughput_mbps is None:
            raise ValueError("At least one metric (latency_ms, packet_loss_pct, throughput_mbps) must be provided unless probe_failed is True")
        return self

class TelemetryResponse(BaseModel):
    id: int
    timestamp: datetime
    source_id: str
    interface: str
    latency_ms: Optional[float] = None
    packet_loss_pct: Optional[float] = None
    throughput_mbps: Optional[float] = None
    bytes_sent: Optional[int] = 0
    bytes_recv: Optional[int] = 0
    probe_failed: bool

    model_config = ConfigDict(from_attributes=True)
