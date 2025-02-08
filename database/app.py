import logging.config
from datetime import datetime as dt
import uuid
import yaml
import logging
import connexion
from connexion import NoContent

from models import JobCompletion, OdometerReport
from utils import create_all_tables, drop_all_tables, create_record, query_records

with open('app_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

def gen_uuid():
    return uuid.uuid4().hex[:24]

def create_tables():
    try:
        create_all_tables()
    except Exception as e:
        return e, 400
    return NoContent, 201

def drop_tables():
    try:
        drop_all_tables()
    except Exception as e:
        return e, 400
    return NoContent, 201
        
def post_cars_odometers(body):
    body['id'] = gen_uuid()
    create_record(body, OdometerReport)
    logger.debug(f"Stored event odometer with trace_id: {body['trace_id']}")

    return NoContent, 201

def post_cars_jobs(body):
    body['id'] = gen_uuid()
    create_record(body, JobCompletion)
    logger.debug(f"Stored event job with trace_id: {body['trace_id']}")

    return NoContent, 201

def get_cars_jobs(start_timestamp, end_timestamp):
    results = query_records(start_timestamp, end_timestamp, JobCompletion)    
    logger.info("Found %d job completions (start: %s, end: %s)", len(results), start_timestamp, end_timestamp)
    return results

def get_cars_odometers(start_timestamp, end_timestamp):
    results = query_records(start_timestamp, end_timestamp, OdometerReport)
    logger.info("Found %d odometer reports (start: %s, end: %s)", len(results), start_timestamp, end_timestamp)
    return results


app = connexion.FlaskApp(__name__, specification_dir='', strict_validation=True)
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8090)