from datetime import datetime, timezone
from sqlalchemy import Column, Integer, Float, String, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from app.db.session import Base

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(Integer, primary_key=True, index=True)
    opened_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    closed_at = Column(DateTime, nullable=True)
    status = Column(String(50), default="active", nullable=False, index=True) # active | acknowledged | dismissed | resolved
    severity = Column(String(50), default="medium", nullable=False, index=True) # low | medium | high | critical
    probable_cause = Column(String(255), nullable=False)
    confidence = Column(Integer, nullable=False, default=0) # 0 to 100
    evidence = Column(JSON, nullable=False, default=list)
    correlated_flags = Column(JSON, nullable=False, default=list)
    symptom_chain = Column(JSON, nullable=False, default=list)

    recommendations = relationship("Recommendation", back_populates="incident", cascade="all, delete-orphan")
    decisions = relationship("HumanDecision", back_populates="incident", cascade="all, delete-orphan")

class Recommendation(Base):
    __tablename__ = "recommendations"

    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(Integer, ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False, index=True)
    action_text = Column(String(500), nullable=False)
    rationale = Column(String(1000), nullable=False)
    safe_to_present = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    incident = relationship("Incident", back_populates="recommendations")
