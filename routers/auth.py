from datetime import datetime, timedelta
from typing import Annotated, Optional
from fastapi import Depends, FastAPI, APIRouter, Form, HTTPException, Request, Response
from jwt import PyJWTError
from pydantic import BaseModel
from database import SessionLocal, engine
from starlette.responses import RedirectResponse
from models import Users
import models
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from starlette import status
import jwt
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import random

SECRET_KEY = "KlgH6AzYDeZeGwD288to79I3vTHT8wp7"
ALGORITHM = "HS256"

templates = Jinja2Templates(directory="templates")
models.Base.metadata.create_all(bind=engine)
oauth2_bearer = OAuth2PasswordBearer(tokenUrl="token")

#Instead of making a whole separate app it routes to the existing one in main.py
router = APIRouter(
    prefix = '/auth',
    tags=['auth']
)
bcrypt_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class LoginForm:
    def __init__(self, request: Request):
        self.request: Request = request
        self.username: Optional[str] = None
        self.password: Optional[str] = None

    async def create_oauth_form(self):
        form = await self.request.form()
        self.username = form.get("email")
        self.password = form.get("password")


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


def get_password_hash(password):
    return bcrypt_context.hash(password)


def verify_password(plain_password, hashed_password):
    return bcrypt_context.verify(plain_password, hashed_password)


def authenticate_user(username: str, password: str, db):
    user = db.query(models.Users)\
        .filter(models.Users.username == username)\
        .first()

    if not user:
        return False
    if not verify_password(password, user.hashed_pass):
        return False
    return user


def create_access_token(username: str, user_id: int,
                        expires_delta: Optional[timedelta] = None):
    encode = {"sub": username, "id": user_id}
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    encode.update({"exp": expire})
    return jwt.encode(encode, SECRET_KEY, algorithm=ALGORITHM)


async def get_curr_user(request: Request):
    try:
        token = request.cookies.get("access_token")
        if token is None:
            return None
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        user_id: int = payload.get("id")
        if username is None or user_id is None:
            logout(request)
        return {"username": username, "id": user_id}
    except PyJWTError:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/token")
async def login_for_access_token(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), 
                                 db: Session = Depends(get_db)):
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        return False
    token_expires = timedelta(minutes=60)
    token = create_access_token(user.username, user.id, expires_delta=token_expires)
    response.set_cookie(key="access_token", value=token, httponly=True)
    return True


@router.get("/login", response_class=HTMLResponse)
async def authentication_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login", response_class=HTMLResponse)
async def login(request: Request, db: Session = Depends(get_db)):
    try:
        form = LoginForm(request)
        await form.create_oauth_form()
        response = RedirectResponse(url="/map", status_code=status.HTTP_302_FOUND)
        validate_user_cookie = await login_for_access_token(response=response, form_data=form, db=db)
        if not validate_user_cookie:
            msg = "Incorrect Username or Password"
            return templates.TemplateResponse("login.html", {"request": request, "msg": msg})
        return response
    except HTTPException:
        msg = "Unknown Error"
        return templates.TemplateResponse("login.html", {"request": request, "msg": msg})


@router.get("/logout")
async def logout(request: Request):
    msg = "Logout Successful"
    response = templates.TemplateResponse("login.html", {"request": request, "msg": msg})
    response.delete_cookie(key="access_token")
    return response


@router.get("/", response_class=HTMLResponse)
async def register(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@router.post("/", response_class=HTMLResponse)
async def register_user(request: Request, email: str = Form(...), username: str = Form(...), 
                        firstname: str = Form(...), lastname: str = Form(...), password: str = Form(...), 
                        password2: str = Form(...), db: Session = Depends(get_db)):
    validation1 = db.query(models.Users).filter(models.Users.username == username).first()
    validation2 = db.query(models.Users).filter(models.Users.email == email).first()
    if password != password2 or validation1 is not None or validation2 is not None:
        msg = "Invalid registration request"
        return templates.TemplateResponse("register.html", {"request": request, "msg": msg})
    user_model = models.Users()
    user_model.username = username
    user_model.email = email
    user_model.firstname = firstname
    user_model.lastname = lastname
    hash_password = get_password_hash(password)
    user_model.hashed_pass = hash_password
    user_model.is_active = True
    user_model.day = 3
    user_model.tag = random.choice(['A1661B', '87894E', '94C7A1', '93CE2D', 'A2AD71'])
    db.add(user_model)
    db.commit()
    msg = "User successfully created"
    return RedirectResponse(url = 'https://www.galapagos.org/')