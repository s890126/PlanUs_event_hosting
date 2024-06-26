from fastapi import FastAPI, Response, status, HTTPException, Depends, Request, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from . import models, schemas, utils, oauth2
from sqlalchemy.orm import Session
from .database import engine, get_db
from .routers import event, user, auth, attend
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
from .config import settings
from datetime import datetime, timedelta
from typing import Dict, List
import logging
import json
from fastapi.middleware.cors import CORSMiddleware


models.Base.metadata.create_all(bind = engine)

app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory = "templates")

app.include_router(event.router)
app.include_router(user.router)
app.include_router(auth.router)
app.include_router(attend.router)

logging.basicConfig(level=logging.INFO)


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logging.info(f"WebSocket connected: {websocket.client}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logging.info(f"WebSocket disconnected: {websocket.client}")

    async def broadcast(self, message: dict):
        message_json = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(message_json)
                logging.info(f"Broadcasting message: {message_json} to {connection.client}")
            except RuntimeError as e:
                logging.error(f"Failed to send message to {connection.client}: {e}")
                self.disconnect(connection)
                logging.info(f"Removed closed connection: {connection.client}")

manager = ConnectionManager()

@app.websocket("/ws/{event_id}")
async def websocket_endpoint(websocket: WebSocket, event_id: int, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user_ws)):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logging.info(f"Received message: {data} from user: {current_user.email}")
            
            parsed_data = json.loads(data)
            message = models.Message(content=parsed_data['content'], user_id=current_user.id, event_id=event_id)
            
            logging.info(f"Creating message: {message}")
            
            db.add(message)
            db.commit()
            
            logging.info(f"Message committed: {message}")
            
            db.refresh(message)
            
            logging.info(f"Message refreshed: {message}")
            
            await manager.broadcast({
                "content": parsed_data['content'],
                "email": current_user.email,
                "user_id": current_user.id
            })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        if websocket.client_state == "CONNECTED":
            await websocket.send_text(json.dumps({"error": str(e)}))
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR)


@app.get("/loginpage", response_class = HTMLResponse)
def home(request : Request):
    context = {'request' : request}
    return templates.TemplateResponse("loginpage.html", context)

@app.get("/signup", response_class = HTMLResponse)
def signup(request : Request):
    context = {'request' : request}
    return templates.TemplateResponse("signuppage.html", context)

@app.get("/create_event", response_class=HTMLResponse)
def get_create_event_form(request: Request):
    return templates.TemplateResponse("create_event.html", {"request": request})

@app.get("/{user_id}/general_profile", response_class=HTMLResponse)
def get_general_profile(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return templates.TemplateResponse("general_profile.html", {"request": request, "user": user})

@app.get("/{user_id}/profile", response_class=HTMLResponse)
def get_profile(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.id != user_id:
        return templates.TemplateResponse("general_profile.html", {"request": request, "user": user})

    now = datetime.utcnow()

    events = db.query(models.Event).filter(
        models.Event.host_id == user_id,
        models.Event.event_time >= now  # Ensure only upcoming events
    ).all()

    joined_events_query = db.query(
        models.Event.id,
        models.Event.title,
        models.Event.event_time,
        models.Event.location
    ).join(
        models.Attend, models.Attend.event_id == models.Event.id
    ).filter(
        models.Attend.user_id == current_user.id,
        models.Event.event_time >= now  # Ensure only upcoming events
    ).order_by(
        models.Event.event_time.asc()
    ).all()

    joined_events = [
        {
            "id": event.id,
            "title": event.title,
            "event_time": event.event_time,
            "location": event.location
        }
        for event in joined_events_query
    ]

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": user,
        "events": events,
        "joined_events": joined_events
    })

@app.post("/{user_id}/upload_profile_picture", response_class=HTMLResponse)
def upload_profile_picture(
    user_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to upload profile picture")

    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No file uploaded")

    # Save the file to a directory
    file_location = f"static/profile_pictures/{user_id}_{file.filename}"
    with open(file_location, "wb+") as file_object:
        shutil.copyfileobj(file.file, file_object)
    
    # Update the user's profile picture path in the database
    user = db.query(models.User).filter(models.User.id == user_id).first()

    # Delete the old profile picture if it exists
    if user.profile_picture:
        old_file_path = user.profile_picture
        if os.path.exists(old_file_path):
            os.remove(old_file_path)

    user.profile_picture = file_location
    db.commit()
    db.refresh(user)

    return RedirectResponse(url=f"/{user_id}/profile", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/{user_id}/update", response_class=HTMLResponse)
def update_profile(
    user_id: int,
    request: Request,
    bio: str = Form(...),
    school : str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(oauth2.get_current_user)
):
    if current_user.id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this profile")

    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.bio = bio
    user.school = school
    db.commit()
    db.refresh(user)

    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

@app.get("/chatrooms", response_class=HTMLResponse)
def user_chatrooms(request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    three_days_ago = datetime.utcnow() - timedelta(days=3)
    chatrooms = (
        db.query(models.Event)
        .join(models.Attend, models.Attend.event_id == models.Event.id)
        .filter(models.Attend.user_id == current_user.id)
        .filter(models.Event.event_time >= three_days_ago)  # Ensure date is in the future or within the last 3 days
        .all()
    )
    return templates.TemplateResponse("chatrooms.html", {"request": request, "chatrooms": chatrooms, "current_user": current_user})
