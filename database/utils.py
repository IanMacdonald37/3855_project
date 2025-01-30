from models import Base

def create_all_tables(engine):
    Base.metadata.create_all(engine)

def drop_all_tables(engine):
    Base.metadata.drop_all(engine)