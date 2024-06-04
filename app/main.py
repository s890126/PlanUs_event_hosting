from fastapi import FastAPI, Response, status, HTTPException, Depends, Request, UploadFile, File, Form
from . import models, schemas, utils, oauth2
from sqlalchemy.orm import Session
from .database import engine, get_db
from .routers import event, user, auth
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import shutil
import os
from .config import settings

models.Base.metadata.create_all(bind = engine)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory = "templates")
app.include_router(event.router)
app.include_router(user.router)
app.include_router(auth.router)

@app.get("/loginpage", response_class = HTMLResponse)
def home(request : Request):
    context = {'request' : request}
    return templates.TemplateResponse("loginpage.html", context)

@app.get("/homepage", response_class = HTMLResponse)
def index(request : Request, current_user : int = Depends(oauth2.get_current_user)):
    context = {'request' : request, 'user' : current_user}
    return templates.TemplateResponse("homepage.html", context)

@app.get("/signup", response_class = HTMLResponse)
def signup(request : Request):
    context = {'request' : request}
    return templates.TemplateResponse("signuppage.html", context)


@app.get("/{user_id}/general_profile", response_class=HTMLResponse)
def get_general_profile(user_id: int, request: Request, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return templates.TemplateResponse("general_profile.html", {"request": request, "user": user})

@app.get("/{user_id}/profile", response_class=HTMLResponse)
def get_profile(user_id: int, request: Request, db: Session = Depends(get_db), current_user: models.User = Depends(oauth2.get_current_user)):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.id != user_id:
        return templates.TemplateResponse("general_profile.html", {"request": request, "user": user})
    
    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

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

    return templates.TemplateResponse("profile.html", {"request": request, "user": user})

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