import logging.config
import connexion
from connexion import NoContent
import yaml
import logging
import json
import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timezone


with open('../config/processing_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('../config/log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

def populate_stats():
    logger.info("Periodic processing started")

    try:
        with open(CONFIG["stats_file"], 'r') as in_file:
            stats = json.load(in_file)
    except:
        stats = {
            "num_odometer_readings": 0,
            "num_jobs_completed": 0,
            "max_odometer_reading": 0,
            "jobs_by_bay": [0,0,0,0,0,0],
            "most_efficient_bay": 0,
            "last_updated": "2000-01-01T01:01:01Z"
        }

    now = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    headers = {"Content-Type" : "application/json"}

    odo_results = httpx.get(f'{CONFIG["urls"]["odo"]}?start_timestamp={stats["last_updated"]}&end_timestamp={now}', headers=headers)
    job_resutls = httpx.get(f'{CONFIG["urls"]["jobs"]}?start_timestamp={stats["last_updated"]}&end_timestamp={now}', headers=headers)

    failed_req = False
    if odo_results.status_code != 200:
        logger.error(f"odo request failed\n\n{odo_results}")
        failed_req = True
    if job_resutls.status_code != 200:
        logger.error(f"job request failed\n\n{job_resutls}") 
        failed_req = True

    if failed_req:
        return None

    num_new_odometer_readings = len(odo_results.json())
    num_new_jobs_completed = len(job_resutls.json())

    logger.info(f"new odometer readings received since last check: {num_new_odometer_readings}")
    logger.info(f"new jobs completed since last check: {num_new_jobs_completed}")

    #calc new stats
    stats["num_odometer_readings"] += num_new_odometer_readings
    stats["num_jobs_completed"] += num_new_jobs_completed

    for odo_reading in odo_results.json():
        if odo_reading["odometer"] > stats["max_odometer_reading"]:
            stats["max_odometer_reading"] = odo_reading["odometer"]
    
    for job in job_resutls.json():
        # Use the bay id (int) from the job details 
        # increment the number of jobs completed in that bay
        stats["jobs_by_bay"][job["bay_id"]-1] += 1

    stats["most_efficient_bay"] = stats["jobs_by_bay"].index(max(stats["jobs_by_bay"])) + 1

    stats["last_updated"] = now

    with open(CONFIG["stats_file"], 'w') as out_file:
        json.dump(stats, out_file, indent=4)

    logger.debug(stats)

    logger.info("periodic processing complete")


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats,
        'interval',
        seconds=CONFIG['scheduler']['interval'])
    sched.start()

def get_stats():
    with open(CONFIG["stats_file"], 'r') as in_file:
        stats = json.load(in_file)
    stats.pop("jobs_by_bay")
    return stats

app = connexion.FlaskApp(__name__, specification_dir='', strict_validation=True)
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100, host="0.0.0.0")