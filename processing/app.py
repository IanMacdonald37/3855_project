import logging.config
import connexion
from connexion import NoContent
import yaml
import logging
import json
import httpx
from apscheduler.schedulers.background import BackgroundScheduler

with open('app_conf.yml', 'r') as f:
    CONFIG = yaml.safe_load(f.read())

with open('log_conf.yml', 'r') as f:
    LOG_CONFIG = yaml.safe_load(f.read())
    logging.config.dictConfig(LOG_CONFIG)

logger = logging.getLogger('basicLogger')

def populate_stats():
    logger.info("Periodic processing started")

    # add a try block
    try:
        with open(CONFIG["stats_file"], 'r') as file:
            stats = json.load(file)
    except:
        stats = {
            "num_odometer_readings": 0,
            "num_jobs_completed": 0,
            "max_odometer_reading": 0,
            "jobs_by_bay": [0,0,0,0,0,0],
            "most_effiecent_bay": 0,
            "last_updated": "2000-01-01 01:01:01"
        }
    
    now = "now" #get date the same way the db does
    headers = {"Content-Type" : "application/json"}

    odo_results = httpx.get(f'{CONFIG["events"]["odo"]["url"]}?start_timestamp={stats["last_updated"]}&end_timestamp={now}', headers=headers)
    job_resutls = httpx.get(f'{CONFIG["events"]["jobs"]["url"]}?start_timestamp={stats["last_updated"]}&end_timestamp={now}', headers=headers)

    #temp
    logger.debug(odo_results)

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

    logger.info(f"new odometer readings received since last check:{num_new_odometer_readings}")
    logger.info(f"new jobs completed since last check:{num_new_jobs_completed}")

    #calc new stats
    stats["num_odometer_reports"] += num_new_odometer_readings
    stats["num_jobs_completed"] += num_new_jobs_completed

    for odo_reading in odo_results.json():
        if odo_reading["odometer"] > stats["max_odometer_reading"]:
            stats["max_odometer_reading"] = odo_reading["odometer"]
    
    for job in job_resutls.json():
        # Use the bay id (int) from the job details 
        # increment the number of jobs completed in that bay
        stats["jobs_by_bay"][job["bay"]-1] += 1

    stats["most_effecient_bay"] = stats["jobs_by_bay"].index(max(stats["jobs_by_bay"])) + 1

    stats["last_update"] = now

    #write to file
    logger.debug(stats)

    logger.info("periodic processing complete")


def init_scheduler():
    sched = BackgroundScheduler(daemon=True)
    sched.add_job(populate_stats,
        'interval',
        seconds=CONFIG['scheduler']['interval'])
    sched.start()

def get_stats():

    return 200, NoContent

app = connexion.FlaskApp(__name__, specification_dir='', strict_validation=True)
app.add_api("openapi.yaml", strict_validation=True, validate_responses=True)

if __name__ == "__main__":
    init_scheduler()
    app.run(port=8100)