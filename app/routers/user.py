from .. import models, schemas, utils, oauth2
from fastapi import FastAPI, Response, status, HTTPException, Depends, APIRouter, Form, UploadFile, File
from sqlalchemy.orm import Session
from ..database import get_db
from fastapi.responses import HTMLResponse
from pydantic import EmailStr
from datetime import date
import shutil
import os


router = APIRouter(
    prefix = "/users",
    tags = ["Users"]
)


@router.post('/', status_code=status.HTTP_201_CREATED)
def create_user(email: EmailStr = Form(...),
    password: str = Form(...),
    birthday: date = Form(...), db : Session = Depends(get_db)):
    existed_user = db.query(models.User).filter(models.User.email == email).first()
    if existed_user:
        content = '''
        <div id="error_response1" class="mb-7 text-center text-red-500 text-xl font-bold">Email is already in use</div>
        <script>
            setTimeout(function() {
                document.getElementById('error_response1').innerHTML = '';
            }, 3000);
        </script>
        '''
        response = HTMLResponse(content = content, status_code = status.HTTP_409_CONFLICT)
        return response

    # hash the password - user.password
    hashed_password = utils.hash(password)
    password = hashed_password
    new_user = models.User(email=email, password=hashed_password, birthday=birthday)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    content = '''
    <div class="mb-7 text-center text-green-500 text-xl font-bold">Signup successful! </br> Redirecting to login page...</div>
    <meta http-equiv="refresh" content="3;url=/">
    <script>
        setTimeout(function() {
            window.location.href = '/';
        }, 3000);
    </script>
    '''
    response = HTMLResponse(content = content, status_code = status.HTTP_201_CREATED)

    return response

@router.get('/{id}', response_model = schemas.UserOut)
def get_user(id : int, db : Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.id == id).first()
    if not user:
        raise HTTPException(status_code = status.HTTP_404_NOT_FOUND, detail = f"User with id: {id} does not exist.")
    return user

