from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class HumanDecisionCreate(BaseModel):
    decision: str = Field(..., pattern="^(approve|reject)$")
    decided_by: Optional[str] = "operator"
    notes: Optional[str] = None

class HumanDecisionResponse(BaseModel):
    id: int
    incident_id: int
    decision: str
    decided_by: str
    decided_at: datetime
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

class RecommendationResponse(BaseModel):
    id: int
    incident_id: int
    action_text: str
    rationale: str
    safe_to_present: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class IncidentResponse(BaseModel):
    id: int
    opened_at: datetime
    closed_at: Optional[datetime] = None
    status: str
    severity: str
    probable_cause: str
    confidence: int
    evidence: List[str] = []
    correlated_flags: List[Dict[str, Any]] = []
    symptom_chain: List[Dict[str, Any]] = []
    recommendations: List[RecommendationResponse] = []
    decisions: List[HumanDecisionResponse] = []

    model_config = ConfigDict(from_attributes=True)
