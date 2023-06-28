from typing import Annotated
from fastapi import Depends, FastAPI, HTTPException, Path, APIRouter
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from models import Users
from database import SessionLocal
from starlette import status
from .auth import get_curr_user
from passlib.context import CryptContext

router = APIRouter(
    prefix = '/user',
    tags = ['user']
)

#opens and closes a connection to the Sessions database
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#Depends establishes a dependancy on get_db so it needs that to work before it starts
db_dep = Annotated[Session, Depends(get_db)]
user_dep = Annotated[dict, Depends(get_curr_user)]
bcrypt_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

class UserVerification(BaseModel):
    password:str
    new_pass: str=Field(min_length=3)


@router.get("/", status_code=status.HTTP_200_OK)
async def get(user: user_dep, db: db_dep):
    if user is None:
        raise HTTPException(status_code=401, detail='User not found')
    return db.query(Users).filter(Users.id == user.get('id')).first()

@router.put("/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_password(user: user_dep, db: db_dep, user_verify: UserVerification):
    if user is None:
        raise HTTPException(status_code=401, detail='User not found')
    user_model = db.query(Users).filter(Users.id == user.get('id')).first()
    if not bcrypt_context.verify(user_verify.password, user_model.hashed_pass):
        raise HTTPException(status_code=401, detail='Error on password change')
    user_model.hashed_pass = bcrypt_context.hash(user_verify.new_pass)
    db.add(user_model)
    db.commit()