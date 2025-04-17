import logging.config
import yaml
import logging
import connexion
import json
from connexion import NoContent
import time
from pykafka import KafkaClient
from pykafka.common import OffsetType

with open('/config/anom_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('/config/log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    LOG_CONFIG['handlers']['file']['filename'] = CONFIG['log_file_name']
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

def test_kafka():
    for i in range(3):  # Retry for 9 seconds
        try:
            client = KafkaClient(hosts=f"kafka:29092")
            topic = client.topics[str.encode(CONFIG['kafka']['topic'])]
            print("Connected to Kafka!")
            break  # Exit loop if connection is successful
        except Exception as e:
            print(f"Kafka connection failed: {e}, retrying...")
            time.sleep(3)
    else:
        raise Exception("Failed to connect to Kafka after multiple attempts")    


def update_anomalies():
    logger.debug("updating...")
    test_kafka()
    
    client = KafkaClient(hosts=f"{CONFIG['kafka']['hostname']}:{CONFIG['kafka']['port']}")
    topic = client.topics[str.encode(CONFIG['kafka']['topic'])]
    consumer = topic.get_simple_consumer(
        reset_offset_on_start=True, consumer_timeout_ms=1000
    )
    anoms = []
    for msg in consumer:
        message = msg.value.decode("utf-8")
        data = json.loads(message)
        if data["type"] == "odometer_report":
            if data["payload"]["odometer"] < CONFIG['min_odometer']:
                anoms.append(
                    {
                        "trace_id": data["payload"]["trace_id"],
                        "event_id": "None",
                        "event_type": data["type"],
                        "anomaly_type": "too low",
                        "description": f"Detected: {data["payload"]["odometer"]}; too low (threshold 1000)"
                    }
                )
                logger.debug(f"value {data["payload"]["odometer"]} was too low and violated min odo rule: { CONFIG['min_odometer']}")
        else:
            if data["payload"]["bay_id"] > CONFIG['max_bay_id']:
                anoms.append(
                    {
                        "trace_id": data["payload"]["trace_id"],
                        "event_id": "None",
                        "event_type": data["type"],
                        "anomaly_type": "too high",
                        "description": f"Detected: {data["payload"]["bay_id"]}; too high (threshold 6)"
                    }
                )
                logger.debug(f"value {data["payload"]["bay_id"]} was too high and violated max bay_id rule: { CONFIG['max_bay_id']}")

    with open(CONFIG["anoms_file"], 'w') as out_file:
        json.dump(anoms, out_file, indent=4)

    return { "anomalies_count": len(anoms)}, 201

def get_anomalies(event_type=None):
    logger.debug(f"getting anoms for {event_type} event")
    if event_type not in ["odometer_report", "job_completion", None]:
        return {"message": f"{event_type} invalid"}, 400
    
    try:
        with open(CONFIG["anoms_file"], 'r') as in_file:
            anoms = json.load(in_file)
        
        if len(anoms) == 0:
            return NoContent, 204

        if event_type == None:
            logger.debug(f"returning {anoms}")
            return anoms, 200
        
        filtered_anoms = []
        for anom in anoms:
            if anom["event_type"] == event_type:
                filtered_anoms.append(anom)

        if len(filtered_anoms) == 0:
            return NoContent, 204
        else:
            logger.debug(f"returning {filtered_anoms}")
            return filtered_anoms, 200
        
    except:
        return {"message": "Something went wrong"}, 404



app = connexion.FlaskApp(__name__, specification_dir='', strict_validation=True)
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    logger.info(f"min_odo: {CONFIG["min_odometer"]}, max_bay_id: {CONFIG['max_bay_id']}")
    app.run(port=8140, host="0.0.0.0")