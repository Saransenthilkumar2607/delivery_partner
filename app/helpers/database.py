from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

Base = declarative_base()

# Import all models to ensure they're registered with SQLAlchemy
from app.models.users import User
from app.models.delivery import Delivery
from app.models.payment import Payment, PaymentRefund

def get_database_session(database_url=None):
    # Use individual environment variables for MySQL by default, fallback to SQLite if no URL provided
    if database_url is None:
        db_name = os.getenv('DB_NAME')
        db_user = os.getenv('DB_USER')
        db_password = os.getenv('DB_PASSWORD')
        db_host = os.getenv('DB_HOST')
        db_port = os.getenv('DB_PORT')
        
        if all([db_name, db_user, db_password, db_host, db_port]):
            database_url = f"mysql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"
        else:
            # Fallback to SQLite if environment variables are not set
            database_url = "sqlite:///db.sqlite3"
    
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()
