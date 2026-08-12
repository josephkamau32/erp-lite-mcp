import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Default to the docker-compose postgres url if not provided
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://erp_user:erp_password@localhost:15432/erp_lite"
)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
