import logging.config
import yaml
import logging
import connexion
import json
from pykafka import KafkaClient

with open('/config/analyzer_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('/config/log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    LOG_CONFIG['handlers']['file']['filename'] = CONFIG['log_file_name']
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

def get_index(type, index):
    client = KafkaClient(hosts=f"{CONFIG['kafka']['hostname']}:{CONFIG['kafka']['port']}")
    topic = client.topics[str.encode(CONFIG['kafka']['topic'])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True, consumer_timeout_ms=1000
    )
    counter = 0
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        if data["type"] == type:
            if counter == index:
                return data["payload"], 200
            counter += 1
        # Look for the index requested and return the payload with 200 status code
    return { "message": f"No message at index {index}!"}, 404

def get_odo(index):
    return get_index("odometer_report", index)

def get_job(index):
    return get_index("job_completion", index)

def get_stats():
    client = KafkaClient(hosts=f"{CONFIG['kafka']['hostname']}:{CONFIG['kafka']['port']}")
    topic = client.topics[str.encode(CONFIG['kafka']['topic'])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True, consumer_timeout_ms=1000
    )
    odo_count = 0
    job_count = 0
    if consumer is None:
        logger.error("Kafka consumer is None. Check if the topic exists.")
        return {"message": "Kafka topic is empty or unreachable"}, 500
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        if data["type"] == "odometer_report":
            odo_count += 1
        elif data["type"] == "job_completion":
            job_count += 1

    return { "num_odometers": odo_count, "num_jobs": job_count}, 200

app = connexion.FlaskApp(__name__, specification_dir='', strict_validation=True)
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    app.run(port=8120, host="0.0.0.0")