from .. import models, schemas
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Request
from starlette.responses import HTMLResponse

from sqlalchemy.orm import Session
from ..database import get_db
from typing import List
from .. import oauth2
from sqlalchemy import func, case
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix = "/events",
    tags = ["Events"]
)

templates = Jinja2Templates(directory = "templates")

@router.get('/partial', response_class=HTMLResponse)
def get_events_partial(request: Request, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    results = db.query(
        models.Event,
        func.count(models.Attend.event_id).label("participants"),
        func.array_agg(models.Attend.user_id).label("participants_ids")
    ).join(
        models.Attend, models.Attend.event_id == models.Event.id, isouter=True
    ).group_by(
        models.Event.id
    ).all()

    events_with_participants = []
    for event, participants, participants_ids in results:
        event_response = schemas.EventResponse.from_orm(event)
        participants_ids = [pid for pid in participants_ids if pid is not None]
        events_with_participants.append({
            "event": event_response,
            "participants": participants,
            "participants_ids": participants_ids
        })

    return templates.TemplateResponse("events_partial.html", {"request": request, "events": events_with_participants, "user": current_user})

@router.get('/', response_class=HTMLResponse)
def events_page(request: Request, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    return templates.TemplateResponse("events.html", {"request": request, "user": current_user})

@router.get('/{id}', response_model = schemas.EventWithParticipants)
def get_event(id: int, db: Session = Depends(get_db), current_user: int = Depends(oauth2.get_current_user)):
    result = db.query(
        models.Event,
        func.count(models.Attend.event_id).label("participants"),
        func.array_agg(models.Attend.user_id).label("participants_ids")
    ).join(
        models.Attend, models.Attend.event_id == models.Event.id, isouter=True
    ).filter(
        models.Event.id == id
    ).group_by(
        models.Event.id
    ).first()

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Event with id: {id} was not found.')

    event, participants, participants_ids = result
    participants_ids = [pid for pid in participants_ids if pid is not None]

    event_response = schemas.EventResponse.from_orm(event)
    event_with_participants = schemas.EventWithParticipants(
        event=event_response,
        participants=participants,
        participants_ids=participants_ids
    )

    return event_with_participants


@router.post('/', status_code = status.HTTP_201_CREATED, response_model = schemas.EventResponse)
def create_events(event : schemas.EventCreate, db : Session = Depends(get_db), current_user : int = Depends(oauth2.get_current_user)):
    new_event = models.Event(host_id = current_user.id, **event.dict())
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    return new_event

@router.put('/{id}')
def update_event(id : int, updated_event : schemas.EventCreate, db : Session = Depends(get_db), current_user : int = Depends(oauth2.get_current_user)):
    event_query = db.query(models.Event).filter(models.Event.id == id)
    event = event_query.first()
    if event == None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = f"event with id: {id} does not exist.")
    if event.host_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail = f"Not authorized to perform requested action")
    event_query.update(updated_event.dict(), synchronize_session = False)
    db.commit()

    return event_query.first()

@router.delete("/{id}", status_code = status.HTTP_204_NO_CONTENT)
def delete_event(id : int, db : Session = Depends(get_db), current_user : int = Depends(oauth2.get_current_user)):
    event = db.query(models.Event).filter(models.Event.id == id)
    if event.first() == None:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = f"event with id: {id} does not exist.")
    if event.first().host_id != current_user.id:
        raise HTTPException(status_code = status.HTTP_403_FORBIDDEN, detail = f"Not authorized to perform requested action")
    event.delete(synchronize_session = False)
    db.commit()

    return Response(status_code = status.HTTP_204_NO_CONTENT)
