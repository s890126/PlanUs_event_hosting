from .. import models, schemas
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Request, Form, File, UploadFile
from starlette.responses import HTMLResponse, RedirectResponse, JSONResponse
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
    current_user: int = Depends(oauth2.get_current_user),
    search_query: str = None
):
    ParticipantUser = aliased(models.User)
    HostUser = aliased(models.User)
    
    now = datetime.utcnow()  # Get the current time in UTC
    
    # Base query for upcoming events with optional search
    base_query = db.query(
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
    )
    
    # Apply search filter
    if search_query:
        search = f"%{search_query}%"
        base_query = base_query.filter(
            (models.Event.title.ilike(search)) |
            (models.Event.location.ilike(search)) |
            (models.Event.tags.any(search_query.upper()))
        )
    
    results = base_query.group_by(
        models.Event.id, HostUser.email, models.Event.picture, models.Event.tags
    ).order_by(
        models.Event.event_time.asc()
    ).all()
    
    # Separate query for top three events with the most participants, without search filter
    top_events_query = db.query(
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
    for event, participants, participants_emails, participants_ids, host_email, picture, tags in top_events:
        event_response = schemas.EventResponse.from_orm(event)
        top_events_with_participants.append({
            "event": event_response,
            "participants": participants,
            "participants_emails": participants_emails,
            "participants_ids": participants_ids,
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


@router.get('/{id}', response_class=HTMLResponse)
def get_event(
    id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    ParticipantUser = aliased(models.User, name="participant_user")
    HostUser = aliased(models.User, name="host_user")

    result = db.query(
        models.Event,
        func.count(models.Attend.event_id).label("participants"),
        func.array_agg(ParticipantUser.email).label("participants_emails"),
        func.array_agg(ParticipantUser.id).label("participants_ids"),
        HostUser.email.label("host_email")  # Get host email
    ).join(
        models.Attend, models.Attend.event_id == models.Event.id, isouter=True
    ).join(
        ParticipantUser, ParticipantUser.id == models.Attend.user_id, isouter=True
    ).join(
        HostUser, HostUser.id == models.Event.host_id
    ).filter(
        models.Event.id == id
    ).group_by(
        models.Event.id, HostUser.email  # Group by event id and host email
    ).first()

    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f'Event with id: {id} was not found.')

    event, participants, participants_emails, participants_ids, host_email = result
    participants_ids = [pid for pid in participants_ids if pid is not None]
    participants_emails = [email for email in participants_emails if email is not None]

    event_response = schemas.EventResponse.from_orm(event)

    # Create zipped data for participants
    participants_data = list(zip(participants_emails, participants_ids))

    # Check if the current user has attended the event
    has_attended = current_user.id in participants_ids

    context = {
        "request": request,
        "event": event_response,
        "participants": participants,
        "participants_data": participants_data,  # Pass the zipped data
        "host_email": host_email,  # Pass host email to template
        "has_attended": has_attended  # Pass attendance status
    }

    return templates.TemplateResponse("event_detail.html", context)


@router.post('/create_event', response_class=HTMLResponse)
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
    tags_list = [tag.strip().upper() for tag in tags.split(',')] if tags else []
    
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


@router.post('/update/{id}', response_class=HTMLResponse)
def update_event_post(
    id: int,
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    event_time: str = Form(...),
    location: str = Form(...),
    picture: UploadFile = File(None),
    current_picture: str = Form(...),
    tags: str = Form(None),
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    event_query = db.query(models.Event).filter(models.Event.id == id)
    event = event_query.first()

    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id: {id} does not exist.")
    if event.host_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")

    event_time = datetime.fromisoformat(event_time)
    tags_list = [tag.strip().upper() for tag in tags.split(',')] if tags else []

    update_data = {
        "title": title,
        "description": description,
        "event_time": event_time,
        "location": location,
        "tags": tags_list
    }

    if picture and picture.filename:
        # Remove the old picture file if it exists and a new picture is provided
        if current_picture and os.path.exists(current_picture):
            os.remove(current_picture)

        # Save the new picture
        picture_filename = f"{event.id}_pic{os.path.splitext(picture.filename)[1]}"
        picture_path = os.path.join("static/images", picture_filename)
        with open(picture_path, "wb") as buffer:
            buffer.write(picture.file.read())
        update_data["picture"] = f"static/images/{picture_filename}"
    else:
        # Keep the old picture if no new picture is uploaded
        update_data["picture"] = current_picture


    print(update_data["picture"], current_picture)
    event_query.update(update_data, synchronize_session=False)
    db.commit()

    user = db.query(models.User).filter(models.User.id == current_user.id).first()
    events = db.query(models.Event).filter(models.Event.host_id == current_user.id).all()

    return templates.TemplateResponse("profile.html", {"request": request, "user": user, "events": events})


@router.delete("/delete/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_event(
    id: int,
    db: Session = Depends(get_db),
    current_user: int = Depends(oauth2.get_current_user)
):
    event_query = db.query(models.Event).filter(models.Event.id == id)
    event = event_query.first()

    if event is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id: {id} does not exist.")
    if event.host_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to perform requested action")
    if event.picture:
        os.remove(event.picture)
    event_query.delete(synchronize_session=False)
    db.commit()
    return RedirectResponse(url=f"/{current_user.id}/profile", status_code=status.HTTP_303_SEE_OTHER)


@router.get("/{event_id}/chat", response_class=HTMLResponse)
def event_chat(request: Request, event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    event = db.query(models.Event).filter(models.Event.id == event_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    attendance = db.query(models.Attend).filter(
        models.Attend.event_id == event_id,
        models.Attend.user_id == current_user.id
    ).first()

    if not attendance:
        raise HTTPException(status_code=403, detail="You are not allowed to access this chat")

    return templates.TemplateResponse("chat.html", {"request": request, "event_id": event_id, "event_title": event.title, "current_user": current_user})


@router.get("/{event_id}/messages", response_class=JSONResponse)
def get_event_messages(event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    messages = (
        db.query(models.Message.content, models.Message.timestamp, models.User.email, models.User.id.label('user_id'))
        .join(models.User, models.Message.user_id == models.User.id)
        .filter(models.Message.event_id == event_id)
        .order_by(models.Message.timestamp.asc())
        .all()
    )
    return {
        "messages": [ {"content": message.content, "timestamp": message.timestamp, "email": message.email, "user_id": message.user_id} for message in messages ],
        "current_user_email": current_user.email,
        "current_user_id": current_user.id
    }
