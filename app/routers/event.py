from .. import models, schemas
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from sqlalchemy.orm import Session
from ..database import get_db
from typing import List
from .. import oauth2

router = APIRouter(
    prefix = "/events",
    tags = ["Events"]
)


@router.get('/', response_model = List[schemas.EventResponse])
def get_events(db : Session = Depends(get_db), user_id : int = Depends(oauth2.get_current_user)):
    events = db.query(models.Event).all()
    return events

@router.get('/{id}', response_model = schemas.EventResponse)
def get_event(id : int, db : Session = Depends(get_db), current_user : int = Depends(oauth2.get_current_user)):
    event = db.query(models.Event).filter(models.Event.id == id).first()
    if not event:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = f'event with id: {id} was not found.')
    return event

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
