from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class HumanDecision(Base):
    __tablename__ = "human_decisions"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    decision = Column(String(50), nullable=False) # approve | reject
    decided_by = Column(String(100), default="operator", nullable=False)
    decided_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    notes = Column(String(500), nullable=True)

    incident = relationship("Incident", back_populates="decisions")
