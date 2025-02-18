import logging.config
import connexion
from connexion import NoContent
import httpx
import time
import yaml
import logging
import json
from pykafka import KafkaClient
import datetime

with open('app_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

client = KafkaClient(hosts=f"{CONFIG['events']['hostname']}:{CONFIG['events']['port']}")
topic = client.topics[str.encode(CONFIG['events']['topic'])]
producer = topic.get_sync_producer()

def gen_uuid():
    return time.time_ns()

def post_cars_odometers(body):
    body["trace_id"] = gen_uuid()
    logger.info(f"Received event odometer with a trace id of {body['trace_id']}")

    # headers = {"Content-Type" : "application/json"}
    # res = httpx.post(CONFIG["events"]["odos"]["url"], json=body, headers=headers)
    # logger.info(f"Response for event odometer (id: {body['trace_id']}) has status {res.status_code}")

    msg = { "type": "odometer_report",
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
        }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))
    logger.info(f"Event with trace_id:{body['trace_id']} sucessfully added to que")

    return NoContent, 201

def post_cars_jobs(body):
    body["trace_id"] = gen_uuid()
    logger.info(f"Received event job with a trace id of {body['trace_id']}")

    # headers = {"Content-Type" : "application/json"}
    # res = httpx.post(CONFIG["events"]["jobs"]["url"], json=body, headers=headers)
    # logger.info(f"Response for event job (id: {body['trace_id']}) has status {res.status_code}")
    
    msg = { "type": "job_completion",
        "datetime": datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "payload": body
        }
    msg_str = json.dumps(msg)
    producer.produce(msg_str.encode('utf-8'))
    logger.info(f"Event with trace_id:{body['trace_id']} sucessfully added to que")

    return NoContent, 201


app = connexion.FlaskApp(__name__, specification_dir='', strict_validation=True)
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8080)