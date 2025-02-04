import logging.config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime as dt
import uuid
import yaml
import logging
import connexion
from connexion import NoContent

from models import JobCompletion, OdometerReport
from utils import create_all_tables, drop_all_tables

with open('app_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

engine = create_engine(f"mysql://{CONFIG['datastore']['user']}:{CONFIG['datastore']['password']}@{CONFIG['datastore']['hostname']}/{CONFIG['datastore']['db']}")
def make_session():
    return sessionmaker(bind=engine)()

def gen_uuid():
    return uuid.uuid4().hex[:24]

def create_tables():
    try:
        create_all_tables(engine)
    except Exception as e:
        return e, 400
    return NoContent, 201

def drop_tables():
    try:
        drop_all_tables(engine)
    except Exception as e:
        return e, 400
    return NoContent, 201
        
def post_cars_odometers(body):
    '''
    Add an entry in the db for the body.VIN 

    OR

    Copare the body.odometer (int) to the next service interval for body.VIN
    If the interval has been met or supassed, book an apointment
    else do nothing
    '''
    session = make_session()
    body['time_stamp'] = dt.strptime(body['time_stamp'], CONFIG["date_format"])
    body['id'] = gen_uuid()
    odo = OdometerReport(**body)
    session.add(odo)
    session.commit()
    session.close()
    logger.debug(f"Stored event odometer with trace_id: {body['trace_id']}")

    return NoContent, 201

def post_cars_jobs(body):
    '''
    Add an entry to the db for the job copleted body.job_id and body.description on car body.VIN
    include the body.bay_id
    
    alert the owner 
    '''
    session = make_session()
    body['time_stamp'] = dt.strptime(body['time_stamp'], CONFIG["date_format"])
    body['id'] = gen_uuid()
    job = JobCompletion(**body)
    session.add(job)
    session.commit()
    session.close()
    logger.debug(f"Stored event job with trace_id: {body['trace_id']}")

    return NoContent, 201

def get_cars_odometers(body):
    session = make_session()
    
    start = dt.fromtimestamp(body["start_timestamp"])
    end = dt.fromtimestamp(body["end_timestamp"])
    
    statement = select(BloodPressure).where(BloodPressure.date_created >= start).where(BloodPressure.date_created < end)
    
    results = [
    result.to_dict()
    for result in session.execute(statement).scalars().all()
    ]
    session.close()
    logger.info("Found %d blood pressure readings (start: %s, end: %s)", len(results), start, end)
    return result


app = connexion.FlaskApp(__name__, specification_dir='', strict_validation=True)
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8090)