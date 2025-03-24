import logging.config
from datetime import datetime as dt
import uuid
import yaml
import logging
import connexion
import json
import time
from threading import Thread
from connexion import NoContent
from pykafka import KafkaClient
from pykafka.common import OffsetType

from models import JobCompletion, OdometerReport
from utils import create_all_tables, drop_all_tables, create_record, query_records

with open('app_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

def setup_kafka_thread():
    t1 = Thread(target=process_messages)
    t1.setDaemon(True)
    t1.start()

def process_messages():
    for i in range(3):  # Retry for 9 seconds
        try:
            client = KafkaClient(hosts=f"kafka:29092")
            topic = client.topics[str.encode(CONFIG['kafka']['topic'])]
            consumer = topic.get_simple_consumer(consumer_group=b'event_group',
                reset_offset_on_start=False,
                auto_offset_reset=OffsetType.LATEST)
            print("Connected to Kafka!")
            break  # Exit loop if connection is successful
        except Exception as e:
            print(f"Kafka connection failed: {e}, retrying...")
            time.sleep(3)
    else:
        raise Exception("Failed to connect to Kafka after multiple attempts")    
    
    # This is blocking - it will wait for a new message
    for msg in consumer:
        msg_str = msg.value.decode('utf-8')
        msg = json.loads(msg_str)
        logger.info("Message: %s" % msg)
        payload = msg["payload"]
        if msg["type"] == "odometer_report":
            new_cars_odometers(payload)
        elif msg["type"] == "job_completion":
            new_cars_jobs(payload)
        # Commit the new message as being read
        consumer.commit_offsets()

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
        
def new_cars_odometers(body):
    body['id'] = gen_uuid()
    create_record(body, OdometerReport)
    logger.debug(f"Stored event odometer with trace_id: {body['trace_id']}")

    return NoContent, 201

def new_cars_jobs(body):
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
    setup_kafka_thread()
    app.run(port=8090, host="0.0.0.0")