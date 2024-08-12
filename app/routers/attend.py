from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Form
from .. import schemas, database, models, oauth2
from sqlalchemy.orm import Session
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse

router = APIRouter(
    prefix = '/attend',
    tags = ['Attend']
)

templates = Jinja2Templates(directory = "templates")

@router.post("/", response_class = HTMLResponse, status_code=status.HTTP_201_CREATED)
def attend(event_id: int = Form(...), 
           db: Session = Depends(database.get_db), current_user: int = Depends(oauth2.get_current_user)):
    attend_query = db.query(models.Attend).filter(models.Attend.event_id == event_id, models.Attend.user_id == current_user.id)
    found_attend = attend_query.first()
    if not found_attend:
        new_attend = models.Attend(event_id=event_id, user_id=current_user.id)
        db.add(new_attend)
        db.commit()
        response = HTMLResponse(status_code = status.HTTP_201_CREATED)
        response.headers['hx-redirect'] = '/events'
        return response
    else:
        attend_query.delete(synchronize_session=False)
        db.commit()
        response = HTMLResponse(status_code = status.HTTP_201_CREATED)
        response.headers['hx-redirect'] = '/events'
        return response



