# 3855 MT
## database and receiver app.py
```python
import logging.config
from datetime import datetime as dt
import uuid
import yaml
import logging
import connexion
import json
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
    client = KafkaClient(hosts=f"{CONFIG['events']['hostname']}:{CONFIG['events']['port']}")
    topic = client.topics[str.encode(CONFIG['events']['topic'])]
    # Create a consume on a consumer group, that only reads new messages
    # (uncommitted messages) when the service re-starts (i.e., it doesn't
    # read all the old messages from the history in the message queue).
    consumer = topic.get_simple_consumer(consumer_group=b'event_group',
        reset_offset_on_start=False,
        auto_offset_reset=OffsetType.LATEST)
    
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
    app.run(port=8090)
```

```python
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
```

## example openapi.yml
```yml
openapi: 3.0.0
info:
  version: 1.0.0
  title: lab
  description: First lab test
paths:
  /db/create:
    post:
      summary: Set up tables
      tags: []
      responses:
        '201':
          description: Created
        '400':
          description: Bad Request
      operationId: app.create_tables
  /db/drop:
    post:
      summary: Drop tables
      tags: []
      responses:
        '201':
          description: Created
        '400':
          description: Bad Request
      operationId: app.drop_tables
  /cars/odometers:
    get:
      operationId: app.get_cars_odometers
      description: Gets odometer reports added after a timestamp
      parameters:
        - name: start_timestamp
          in: query
          description: Limits the number of readings returned
          schema:
            type: string
            format: date-time
            example: 2016-08-29T09:12:33.001Z
        - name: end_timestamp
          in: query
          description: Limits the number of readings returned
          schema:
            type: string
            format: date-time
            example: 2016-08-29T09:12:33.001Z
      responses:
        '200':
          description: Successfully returned a list of odos
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/OdometerReport'
  /cars/jobs:
    get:
      operationId: app.get_cars_jobs
      description: Gets jobs added after a timestamp
      parameters:
        - name: start_timestamp
          in: query
          description: Limits the number of readings returned
          schema:
            type: string
            format: date-time
            example: 2016-08-29T09:12:33.001Z
        - name: end_timestamp
          in: query
          description: Limits the number of readings returned
          schema:
            type: string
            format: date-time
            example: 2016-08-29T09:12:33.001Z
      responses:
        '200':
          description: Successfully returned a list of jobs
          content:
            application/json:
              schema:
                type: array
                items:
                  $ref: '#/components/schemas/JobCompletion'
components:
  schemas:
    OdometerReport:
      type: object
      title: Odometer Report
      required: 
        - owner_id
        - odometer
        - VIN
        - time_stamp
        - trace_id
      properties:
        VIN:
          type: string
        owner_id:
          type: string
        odometer:
          type: integer
          x-stoplight:
            id: d16ed74vidddq
        time_stamp:
          type: string
          x-stoplight:
            id: rhmtg7j6vxl2e
        trace_id:
          type: integer
    JobCompletion:
      title: Job Completion
      type: object
      required: 
        - job_id
        - bay_id
        - VIN
        - description
        - time_stamp
        - trace_id
      properties:
        job_id:
          type: string
        bay_id:
          type: integer
          x-stoplight:
            id: vvt5znexj0xsl
          format: int64
        VIN:
          type: string
          x-stoplight:
            id: 998l2byl3mvp0
        description:
          type: string
          x-stoplight:
            id: 3ve4d2nqa7bix
        time_stamp:
          type: string
          x-stoplight:
            id: gb8bm0qtifo67
          format: date-time
        trace_id:
          type: integer      
```

## Log conf
```yml
version: 1
formatters:
  simple:
    format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
handlers:
  console:
    class: logging.StreamHandler
    level: DEBUG
    formatter: simple
    stream: ext://sys.stdout
  file:
    class: logging.FileHandler
    level: DEBUG
    formatter: simple
    filename: app.log
loggers:
 basicLogger:
    level: DEBUG
    handlers: [console, file]
    propagate: no
root:
  level: DEBUG
  handlers: [console]
disable_existing_loggers: false
```
