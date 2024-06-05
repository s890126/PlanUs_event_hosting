from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter
from .. import schemas, database, models, oauth2
from sqlalchemy.orm import Session

router = APIRouter(
    prefix = '/attend',
    tags = ['Attend']
)

@router.post("/", status_code = status.HTTP_201_CREATED)
def attend(attend : schemas.Attend, db : Session = Depends(database.get_db), current_user : int = Depends(oauth2.get_current_user)):
    attend_query = db.query(models.Attend).filter(models.Attend.event_id == attend.event_id, models.Attend.user_id == current_user.id)
    found_attend = attend_query.first()
    if not found_attend:
        new_attend = models.Attend(event_id = attend.event_id, user_id = current_user.id)
        db.add(new_attend)
        db.commit()
        return {"message" : "successfully attended"}
    else:
        attend_query.delete(synchronize_session = False)
        db.commit()
        return {"message" : "successfully unattended"}

