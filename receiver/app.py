import logging.config
import connexion
from connexion import NoContent
import httpx
import time
import yaml
import logging

with open('app_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

def gen_uuid():
    return time.time_ns()

def post_cars_odometers(body):
    '''
    Add an entry in the db for the body.VIN 

    OR

    Copare the body.odometer (int) to the next service interval for body.VIN
    If the interval has been met or supassed, book an apointment
    else do nothing
    '''
    body["trace_id"] = gen_uuid()
    logger.info(f"Received event odometer with a trace id of {body['trace_id']}")

    headers = {"Content-Type" : "application/json"}
    res = httpx.post(CONFIG["events"]["odos"]["url"], json=body, headers=headers)
    logger.info(f"Response for event odometer (id: {body['trace_id']}) has status {res.status_code}")


    return NoContent, res.status_code

def post_cars_jobs(body):
    '''
    Add an entry to the db for the job copleted body.job_id and body.description on car body.VIN
    include the body.bay_id
    
    alert the owner 
    '''
    body["trace_id"] = gen_uuid()
    logger.info(f"Received event job with a trace id of {body['trace_id']}")

    headers = {"Content-Type" : "application/json"}
    res = httpx.post(CONFIG["events"]["jobs"]["url"], json=body, headers=headers)
    logger.info(f"Response for event job (id: {body['trace_id']}) has status {res.status_code}")


    return NoContent, res.status_code


app = connexion.FlaskApp(__name__, specification_dir='', strict_validation=True)
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)