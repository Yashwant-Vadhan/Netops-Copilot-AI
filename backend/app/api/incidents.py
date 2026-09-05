from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, Path, Body, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.db.session import get_db
from app.models.incident import Incident, Recommendation
from app.models.human_decision import HumanDecision
from app.schemas.incident import HumanDecisionCreate, IncidentResponse
from app.agents import correlation_engine, diagnosis_agent, recommendation_agent, safety_governor
from app.core.errors import APIException, success_response

router = APIRouter(prefix="/incidents", tags=["incidents"])

def orchestrate_reasoning_pipeline(flags: List[dict], telemetry_context: dict, db: Session) -> Optional[Incident]:
    """
    Orchestrates:
    correlation_engine.correlate() -> diagnosis_agent.diagnose() ->
    recommendation_agent.recommend() -> safety_governor.check()
    and persists an Incident + Recommendation row in DB.
    """
    clusters = correlation_engine.correlate(flags)
    if not clusters:
        return None

    incidents_created = []
    for cluster in clusters:
        correlated_flags = cluster.get("correlated_flags", [])
        symptom_chain = cluster.get("symptom_chain", [])

        diag_res = diagnosis_agent.diagnose(correlated_flags, telemetry_context)
        probable_cause = diag_res.get("probable_cause", "unknown_issue")
        confidence = diag_res.get("confidence", 50)
        evidence = diag_res.get("evidence", [])

        # Determine severity based on metric flags
        severity = "medium"
        metrics_flagged = {f.get("metric") for f in correlated_flags}
        if len(metrics_flagged) >= 3 or "packet_loss_pct" in metrics_flagged and "latency_ms" in metrics_flagged:
            severity = "critical"
        elif "packet_loss_pct" in metrics_flagged or "latency_ms" in metrics_flagged:
            severity = "high"
        elif "throughput_mbps" in metrics_flagged:
            severity = "medium"
        else:
            severity = "low"

        rec_res = recommendation_agent.recommend(probable_cause, severity, evidence)
        governed_rec = safety_governor.check(rec_res)

        incident = Incident(
            opened_at=datetime.now(timezone.utc),
            status="active",
            severity=severity,
            probable_cause=probable_cause,
            confidence=confidence,
            evidence=evidence,
            correlated_flags=correlated_flags,
            symptom_chain=symptom_chain
        )
        db.add(incident)
        db.flush()

        recommendation = Recommendation(
            incident_id=incident.id,
            action_text=governed_rec.get("action_text", ""),
            rationale=governed_rec.get("rationale", ""),
            safe_to_present=governed_rec.get("safe_to_present", True),
            created_at=datetime.now(timezone.utc)
        )
        db.add(recommendation)
        incidents_created.append(incident)

    db.commit()
    for inc in incidents_created:
        db.refresh(inc)

    return incidents_created[0] if incidents_created else None


@router.post("/pipeline", status_code=status.HTTP_201_CREATED)
def trigger_pipeline(
    payload: dict = Body(...),
    db: Session = Depends(get_db)
):
    """
    Endpoint to trigger reasoning pipeline with raw flags + telemetry context.
    """
    flags = payload.get("flags", [])
    telemetry_context = payload.get("telemetry_context", {})
    incident = orchestrate_reasoning_pipeline(flags, telemetry_context, db)
    if not incident:
        raise APIException(status_code=400, code="NO_FLAGS", message="No valid clusters produced from flags")
    
    # Reload with relationships
    inc_db = db.query(Incident).options(
        joinedload(Incident.recommendations),
        joinedload(Incident.decisions)
    ).filter(Incident.id == incident.id).first()

    data = IncidentResponse.model_validate(inc_db).model_dump(mode="json")
    return success_response(data=data, status_code=status.HTTP_201_CREATED)


@router.get("")
def list_incidents(
    status: Optional[str] = Query(None, description="Filter by status (active|acknowledged|dismissed|resolved)"),
    severity: Optional[str] = Query(None, description="Filter by severity (low|medium|high|critical)"),
    db: Session = Depends(get_db)
):
    query = db.query(Incident).options(
        joinedload(Incident.recommendations),
        joinedload(Incident.decisions)
    )
    if status:
        query = query.filter(Incident.status == status)
    if severity:
        query = query.filter(Incident.severity == severity)

    incidents = query.order_by(desc(Incident.opened_at)).all()
    data = [IncidentResponse.model_validate(inc).model_dump(mode="json") for inc in incidents]
    return success_response(data=data)


@router.get("/{incident_id}")
def get_incident(
    incident_id: int = Path(..., description="Incident ID"),
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).options(
        joinedload(Incident.recommendations),
        joinedload(Incident.decisions)
    ).filter(Incident.id == incident_id).first()

    if not incident:
        raise APIException(status_code=404, code="NOT_FOUND", message=f"Incident with ID {incident_id} not found")

    data = IncidentResponse.model_validate(incident).model_dump(mode="json")
    return success_response(data=data)


@router.patch("/{incident_id}/decision")
def record_decision(
    incident_id: int = Path(...),
    payload: HumanDecisionCreate = Body(...),
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).options(
        joinedload(Incident.recommendations),
        joinedload(Incident.decisions)
    ).filter(Incident.id == incident_id).first()

    if not incident:
        raise APIException(status_code=404, code="NOT_FOUND", message=f"Incident with ID {incident_id} not found")

    decision_rec = HumanDecision(
        incident_id=incident.id,
        decision=payload.decision,
        decided_by=payload.decided_by or "operator",
        decided_at=datetime.now(timezone.utc),
        notes=payload.notes
    )
    db.add(decision_rec)

    # Update incident status
    if payload.decision == "approve":
        incident.status = "acknowledged"
    elif payload.decision == "reject":
        incident.status = "dismissed"

    db.commit()
    db.refresh(incident)

    data = IncidentResponse.model_validate(incident).model_dump(mode="json")
    return success_response(data=data)


@router.patch("/{incident_id}/status")
def update_incident_status(
    incident_id: int = Path(...),
    new_status: str = Query(..., description="New status (active|acknowledged|dismissed|resolved)"),
    db: Session = Depends(get_db)
):
    incident = db.query(Incident).options(
        joinedload(Incident.recommendations),
        joinedload(Incident.decisions)
    ).filter(Incident.id == incident_id).first()

    if not incident:
        raise APIException(status_code=404, code="NOT_FOUND", message=f"Incident with ID {incident_id} not found")

    # SERVER-SIDE GUARD: Cannot transition to "resolved" without an existing HumanDecision row
    if new_status == "resolved":
        has_decision = len(incident.decisions) > 0
        if not has_decision:
            raise APIException(
                status_code=400,
                code="HUMAN_DECISION_REQUIRED",
                message="Cannot mark incident as resolved without a recorded human decision."
            )
        incident.closed_at = datetime.now(timezone.utc)

    incident.status = new_status
    db.commit()
    db.refresh(incident)

    data = IncidentResponse.model_validate(incident).model_dump(mode="json")
    return success_response(data=data)


@router.get("/{incident_id}/similar")
def get_similar_incidents(
    incident_id: int = Path(..., description="Target Incident ID"),
    limit: int = Query(3, ge=1, le=10, description="Max similar incidents to return"),
    db: Session = Depends(get_db)
):
    target = db.query(Incident).filter(Incident.id == incident_id).first()
    if not target:
        raise APIException(status_code=404, code="NOT_FOUND", message=f"Incident with ID {incident_id} not found")

    candidates = (
        db.query(Incident)
        .options(
            joinedload(Incident.recommendations),
            joinedload(Incident.decisions)
        )
        .filter(Incident.id != incident_id, Incident.probable_cause == target.probable_cause)
        .all()
    )

    if not candidates:
        return success_response(data=[])

    def tokenize(text_list: list) -> set:
        words = set()
        for text in text_list:
            if isinstance(text, str):
                for w in text.lower().replace(".", " ").replace(",", " ").split():
                    if len(w) > 2:
                        words.add(w)
        return words

    target_words = tokenize(target.evidence or [])

    matches = []
    for cand in candidates:
        cand_words = tokenize(cand.evidence or [])
        intersection = target_words.intersection(cand_words)
        union = target_words.union(cand_words)
        jaccard = (len(intersection) / len(union)) if union else 0.0

        # Base similarity score from cause match (50%) + evidence overlap (35%) + severity match (15%)
        base_score = 50.0 + (jaccard * 35.0) + (15.0 if cand.severity == target.severity else 0.0)
        score = round(min(100.0, base_score), 1)

        matching_factors = [f"Matching probable cause: {target.probable_cause}"]
        if cand.severity == target.severity:
            matching_factors.append(f"Matching severity level: {target.severity}")
        if intersection:
            matching_factors.append(f"Shared evidence terms: {', '.join(sorted(list(intersection))[:4])}")

        cand_data = IncidentResponse.model_validate(cand).model_dump(mode="json")
        matches.append({
            "incident": cand_data,
            "similarity_score": score,
            "matching_factors": matching_factors
        })

    matches.sort(key=lambda x: x["similarity_score"], reverse=True)
    return success_response(data=matches[:limit])

