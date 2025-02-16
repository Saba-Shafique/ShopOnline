# from sqlalchemy import create_engine
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import sessionmaker

# DATABASE_URL = "postgresql://postgres:saba123@localhost/shopOnlineDBtest"

# engine = create_engine(DATABASE_URL)

# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()

# def init_db():
#     """Create the database tables."""
#     Base.metadata.create_all(bind=engine)


from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base  # Updated import
from sqlalchemy.exc import SQLAlchemyError

DATABASE_URL = "postgresql://postgres:saba123@localhost/shopOnlineWebDB"

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()  # Updated to use SQLAlchemy 2.0 declarative_base

def init_db():
    """Create the database tables."""
    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as e:
        print(f"Error initializing the database: {e}")
