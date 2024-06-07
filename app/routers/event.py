from .. import models, schemas
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Request, Form, File, UploadFile
from starlette.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import aliased
from sqlalchemy.orm import Session
from ..database import get_db
from typing import List
from .. import oauth2
from sqlalchemy import func, case
from fastapi.templating import Jinja2Templates
from datetime import datetime
import os
from fastapi.staticfiles import StaticFiles

router = APIRouter(
    prefix = "/events",
    tags = ["Events"]
)

templates = Jinja2Templates(directory = "templates")
router.mount("/static", StaticFiles(directory="static"), name="static")

@router.get('/partial', response_class=HTMLResponse)
def get_events_partial(
    request: Request,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    ParticipantUser = aliased(models.User)
    HostUser = aliased(models.User)
    
    now = datetime.utcnow()  # Get the current time in UTC
    
    # Query to get all upcoming events
    results = db.query(
        models.Event,
        func.count(models.Attend.event_id).label("participants"),
        func.array_agg(ParticipantUser.email).label("participants_emails"),
        func.array_agg(ParticipantUser.id).label("participants_ids"),  # Add participant IDs
        HostUser.email.label("host_email"),
        models.Event.picture,
        models.Event.tags
    ).join(
        models.Attend, models.Attend.event_id == models.Event.id, isouter=True
    ).join(
        HostUser, HostUser.id == models.Event.host_id
    ).join(
        ParticipantUser, ParticipantUser.id == models.Attend.user_id, isouter=True
    ).filter(
        models.Event.event_time >= now  
    ).group_by(
        models.Event.id, HostUser.email, models.Event.picture, models.Event.tags
    ).order_by(
        models.Event.event_time.asc()  
    ).all()
    
    # Query to get the top three events with the most participants
    top_events_query = db.query(
        models.Event,
        func.count(models.Attend.event_id).label("participants"),
        HostUser.email.label("host_email"),
        models.Event.picture,
        models.Event.tags
    ).join(
        models.Attend, models.Attend.event_id == models.Event.id, isouter=True
    ).join(
        HostUser, HostUser.id == models.Event.host_id
    ).filter(
        models.Event.event_time >= now
    ).group_by(
        models.Event.id, HostUser.email, models.Event.picture, models.Event.tags
    ).order_by(
        func.count(models.Attend.event_id).desc()
    ).limit(3)
    
    top_events = top_events_query.all()
    
    events_with_participants = []
    for event, participants, participants_emails, participants_ids, host_email, picture, tags in results:
        event_response = schemas.EventResponse.from_orm(event)
        participants_emails = [email for email in participants_emails]
        participants_ids = [pid for pid in participants_ids]  
        has_attended = current_user.id in participants_ids  
        events_with_participants.append({
            "event": event_response,
            "participants": participants,
            "participants_emails": participants_emails,
            "participants_ids": participants_ids,
            "host_email": host_email,
            "picture": picture,
            "tags": tags,
            "has_attended": has_attended  
        })
    
    top_events_with_participants = []
    for event, participants, host_email, picture, tags in top_events:
        event_response = schemas.EventResponse.from_orm(event)
        top_events_with_participants.append({
            "event": event_response,
            "participants": participants,
            "host_email": host_email,
            "picture": picture,
            "tags": tags
        })
    
    return templates.TemplateResponse("events_partial.html", {
        "request": request,
        "events": events_with_participants,
        "top_events": top_events_with_participants,
        "user": current_user
    })


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


@router.post('/create_event', response_class = HTMLResponse)
def create_event(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    event_time: str = Form(...),
    location: str = Form(...),
    picture: UploadFile = File(None),
    tags: str = Form(None),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    event_time = datetime.fromisoformat(event_time)
    tags_list = [tag.strip() for tag in tags.split(',')] if tags else []
    
    new_event = models.Event(
        title=title,
        description=description,
        event_time=event_time,
        location=location,
        picture=None,  # Temporarily set to None
        tags=tags_list,
        host_id=current_user.id
    )
    db.add(new_event)
    db.commit()
    db.refresh(new_event)

    # Rename and save the picture using event_id
    if picture:
        picture_filename = f"{new_event.id}_pic{os.path.splitext(picture.filename)[1]}"
        picture_path = os.path.join("static/images", picture_filename)
        with open(picture_path, "wb") as buffer:
            buffer.write(picture.file.read())
        new_event.picture = f"static/images/{picture_filename}"
        db.commit()

    # Check if the host is already attending the event to avoid duplicate key error
    existing_attendance = db.query(models.Attend).filter(
        models.Attend.event_id == new_event.id,
        models.Attend.user_id == current_user.id
    ).first()

    if not existing_attendance:
        new_attendance = models.Attend(event_id=new_event.id, user_id=current_user.id)
        db.add(new_attendance)
        db.commit()
        db.refresh(new_attendance)

    return RedirectResponse(url="/events", status_code=status.HTTP_303_SEE_OTHER)

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
