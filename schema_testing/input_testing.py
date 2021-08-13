from sqlalchemy import create_engine
from config import DATABASE_URI
from sqlalchemy.orm import sessionmaker
engine = create_engine(DATABASE_URI)
from models import Base, User

Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)

from contextlib import contextmanager

@contextmanager
def session_scope():
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

def recreate_database():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

with session_scope() as s:
    # TODO this is where we need to read in the input excel workbooks and coerse them into
    # proper database objects.
    recreate_database()
    user = s.query(User).all()
    foo = "bar"
    