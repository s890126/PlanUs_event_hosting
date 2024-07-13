from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy.orm import Session
from ..database import get_db
from .. import schemas, models, utils, oauth2
from fastapi.security.oauth2 import OAuth2PasswordRequestForm
from fastapi.responses import HTMLResponse


router = APIRouter(tags = ['Authentication'])

@router.post('/login', response_class = HTMLResponse)
def login(user_credentials : OAuth2PasswordRequestForm = Depends(), db : Session = Depends(get_db)):

    user = db.query(models.User).filter(models.User.email == user_credentials.username).first()

    if not user or not utils.verify(user_credentials.password, user.password):
        content = '<div class="mb-7 text-center text-red-500 text-xl font-bold" >Wrong email or password</div>'
        response =  HTMLResponse(content = content, status_code = status.HTTP_403_FORBIDDEN)
        return response
    
    # create a token

    access_token = oauth2.create_access_token(data = {"user_id" : user.id})
    content = "<div>Login successful!</div>"
    response = HTMLResponse(content = content, status_code = status.HTTP_200_OK)
    response.set_cookie(key = "access_token", value = access_token, httponly = True, path = "/")
    response.headers['hx-redirect'] = '/events'
    return response

@router.post('/logout', response_class=HTMLResponse)
def logout():
    content = "<div>Logout successful!</div>"
    response = HTMLResponse(content=content, status_code=status.HTTP_200_OK)
    response.delete_cookie(key= "access_token", path="/")
    response.headers['hx-redirect'] = '/'
    return response