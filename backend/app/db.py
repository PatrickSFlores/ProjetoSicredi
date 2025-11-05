import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

USER = os.environ.get("POSTGRES_USER")
PWD  = os.environ.get("POSTGRES_PASSWORD")
DB   = os.environ.get("POSTGRES_DB")
HOST = os.environ.get("POSTGRES_HOST", "db")
PORT = os.environ.get("POSTGRES_PORT", "5432")

DATABASE_URL = f"postgresql+psycopg2://{USER}:{PWD}@{HOST}:{PORT}/{DB}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
