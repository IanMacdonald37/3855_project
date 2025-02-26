# 3855 MT
## Receiver app.py
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
  /cars/odometers:
    post:
      summary: Your POST endpoint
      tags: []
      responses:
        '201':
          description: Created
        '400':
          description: Bad Request
      operationId: app.post_cars_odometers
      requestBody:
        description: Current odometer readings for a car
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/OdometerReport'
  /cars/jobs:
    post:
      summary: Your POST endpoint
      tags: []
      responses:
        '201':
          description: Created
        '400':
          description: Bad Request
      operationId: app.post_cars_jobs
      requestBody:
        description: Service jobs completed for a specific car
        content:
          application/json:
            schema:
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
    JobCompletion:
      title: Job Completion
      type: object
      required: 
        - job_id
        - bay_id
        - VIN
        - description
        - time_stamp
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
```
