import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from .. import create_app
from ..services.maintenance_engine import run_cycle

def main():
    app=create_app()
    # Separate process by design: the Flask reloader and web workers never start jobs.
    with app.app_context():
        from ..extensions import db
        db.engine.connect().close()
    scheduler=BlockingScheduler(timezone=app.config["TIMEZONE"],jobstores={"default":MemoryJobStore()},executors={"default":ThreadPoolExecutor(1)})
    def job():
        with app.app_context():
            try: logging.info("Maintenance cycle: %s",run_cycle())
            except Exception: logging.exception("Scheduled maintenance failed")
    scheduler.add_job(job,"interval",minutes=app.config["CHECK_INTERVAL_MINUTES"],id="maintenance",max_instances=1,coalesce=True,misfire_grace_time=300)
    logging.info("Scheduler started; interval=%s minutes timezone=%s",app.config["CHECK_INTERVAL_MINUTES"],app.config["TIMEZONE"])
    scheduler.start()

if __name__ == "__main__": main()
