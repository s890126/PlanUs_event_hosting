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
        feedback_message = """
            Joined the event! <br>
            <span class="inline-flex items-center text-2xl">
                Click on 
                <svg xmlns="https://www.w3.org/2000/svg" class="h-10 w-10 cursor-pointer ml-2 mr-2" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.276 8.276 0 01-3.358-.714l-3.96.992a1 1 0 01-1.215-1.215l.993-3.96A8.276 8.276 0 012 10c0-3.866 3.582-7 8-7s8 3.134 8 7zm-8-5a5 5 0 100 10 5 5 0 000-10z" clip-rule="evenodd" />
                </svg>
                to chat with other participants!
            </span>
        """
    else:
        attend_query.delete(synchronize_session=False)
        db.commit()
        feedback_message = 'Left the event!'

    html_content = f"""
        <html>
        <head>
            <meta https-equiv="refresh" content="3;url=/events" />
            <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
        </head>
        <body class="flex items-center justify-center min-h-screen bg-gray-100">
            <div class="bg-white p-6 rounded-lg shadow-md text-center">
                <p class="text-2xl text-gray-700">{feedback_message}</p>
                <script>
                    setTimeout(function() {{
                        window.location.href = '/events';
                    }}, 3000);
                </script>
            </div>
        </body>
        </html>
    """
    return HTMLResponse(content=html_content, status_code=status.HTTP_200_OK)



