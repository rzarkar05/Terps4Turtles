from database import Base
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey

#Inheirits base which allows it to be a table
class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True) #Since prmary key automatically gets iterated
    email = Column(String)
    username = Column(String, unique=True)
    firstname = Column(String)
    lastname = Column(String)
    hashed_pass = Column(String)
    day = Column(Integer)
    tag = Column(String)
    is_active = Column(Boolean, default=True)
    role = Column(String)