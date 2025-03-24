from models import Base
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
import yaml
from datetime import datetime as dt


with open('/config/storage_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

engine = create_engine(f"mysql://{CONFIG['datastore']['user']}:{CONFIG['datastore']['password']}@{CONFIG['datastore']['hostname']}/{CONFIG['datastore']['db']}")
def make_session():
    return sessionmaker(bind=engine)()

def create_all_tables():
    Base.metadata.create_all(engine)

def drop_all_tables():
    Base.metadata.drop_all(engine)

def create_record(body, class_type):
    session = make_session()

    body['time_stamp'] = dt.strptime(body['time_stamp'], CONFIG["date_format"])
    
    entry = class_type(**body)
    
    session.add(entry)
    
    session.commit()
    session.close()

def query_records(start, end, class_type):
    session = make_session()

    statement = select(class_type).where(class_type.date_created >= start).where(class_type.date_created < end)
    
    results = [
    result.to_dict()
    for result in session.execute(statement).scalars().all()
    ]
    session.close()
    return results