from sqlalchemy import Column, Integer, String

from core.config import database_setup

Base, engine = database_setup()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)

# Create tables in the database
Base.metadata.create_all(bind=engine)
