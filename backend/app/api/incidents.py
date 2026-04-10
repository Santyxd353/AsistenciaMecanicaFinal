from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.db.session import get_session
from app.models.domain import Incident, IncidentCreate, IncidentRead
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=IncidentRead)
def create_incident(*, session: Session = Depends(get_session), incident_in: IncidentCreate):
    incident = Incident.from_orm(incident_in)
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident

@router.get("/", response_model=List[IncidentRead])
def read_incidents(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
):
    incidents = session.exec(select(Incident).offset(skip).limit(limit)).all()
    return incidents

@router.get("/{incident_id}", response_model=IncidentRead)
def read_incident(
    *, session: Session = Depends(get_session), incident_id: int
):
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident

@router.patch("/{incident_id}/status", response_model=IncidentRead)
def update_incident_status(
    *, session: Session = Depends(get_session), incident_id: int, status: str
):
    incident = session.get(Incident, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    incident.status = status
    session.add(incident)
    session.commit()
    session.refresh(incident)
    return incident
