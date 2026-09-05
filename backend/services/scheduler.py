import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Ensure the backend directory is in the system path to allow absolute imports
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.append(str(BASE_DIR))

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("services.scheduler")

# Global reference to the background scheduler
scheduler = BackgroundScheduler()

def daily_forecast_refresh_job():
    """
    Job placeholder to refresh the demand forecast outputs.
    Normally triggers the inference pipelines.
    """
    logger.info("Scheduler Event: Running Daily Demand Forecast Refresh...")
    # Simulates loading model and updating the JSON results
    logger.info("Scheduler Event: Daily Demand Forecast Refresh finished successfully.")

def weekly_retraining_job():
    """
    Job placeholder to retrain machine learning pricing and forecasting models.
    Does not run actual training routines.
    """
    logger.info("Scheduler Event: Running Weekly Model Retraining (Simulation)...")
    logger.info("Scheduler Event: Weekly Model Retraining completed successfully.")

def monthly_evaluation_job():
    """
    Job placeholder to run monthly holdout evaluation and generate performance metrics.
    """
    logger.info("Scheduler Event: Running Monthly Model Evaluation...")
    logger.info("Scheduler Event: Monthly Model Evaluation completed successfully.")

def competitor_monitoring_job():
    """
    Scheduled job to run the competitor monitoring cycle periodically.
    """
    logger.info("Scheduler Event: Starting scheduled Competitor Price Monitoring cycle...")
    from services.competitor_monitoring_service import CompetitorMonitoringService
    from main import SessionLocal
    
    db_conn = SessionLocal()
    try:
        service = CompetitorMonitoringService()
        results = service.run_monitoring_cycle(db_conn, force_all=False)
        logger.info(f"Scheduler Event: Competitor Price Monitoring cycle finished. Results: {results}")
    except Exception as e:
        logger.error(f"Scheduler Event: Competitor Price Monitoring job failed: {e}")
    finally:
        db_conn.close()

def start_scheduler() -> bool:
    """
    Initializes triggers, registers target jobs, and starts the background scheduler thread.
    """
    global scheduler
    
    # Check if the scheduler is already running
    if scheduler.running:
        logger.warning("Scheduler is already running.")
        return False
        
    try:
        # 1. Register Daily Demand Forecast Refresh: Every day at 00:00 midnight
        scheduler.add_job(
            daily_forecast_refresh_job,
            CronTrigger(hour=0, minute=0),
            id="daily_forecast_refresh",
            name="Daily Demand Forecast Refresh",
            replace_existing=True
        )
        
        # 2. Register Weekly Model Retraining: Every Sunday at 01:00 AM
        scheduler.add_job(
            weekly_retraining_job,
            CronTrigger(day_of_week="sun", hour=1, minute=0),
            id="weekly_model_retraining",
            name="Weekly Model Retraining (Simulation)",
            replace_existing=True
        )
        
        # 3. Register Monthly Model Evaluation: First day of every month at 02:00 AM
        scheduler.add_job(
            monthly_evaluation_job,
            CronTrigger(day=1, hour=2, minute=0),
            id="monthly_model_evaluation",
            name="Monthly Model Evaluation",
            replace_existing=True
        )
        
        # 4. Register Competitor Price Monitoring: periodic interval
        monitoring_enabled = os.getenv("COMPETITOR_MONITORING_ENABLED", "true").lower() == "true"
        if monitoring_enabled:
            try:
                interval_hours = int(os.getenv("COMPETITOR_SCAN_INTERVAL_HOURS", "6"))
            except ValueError:
                interval_hours = 6

            scheduler.add_job(
                competitor_monitoring_job,
                "interval",
                hours=interval_hours,
                id="competitor_monitoring",
                name="Competitor Price Monitoring",
                replace_existing=True
            )
            logger.info(f"Registered Competitor Price Monitoring job to run every {interval_hours} hours.")
        else:
            logger.info("Competitor Price Monitoring job is disabled via COMPETITOR_MONITORING_ENABLED.")
        
        # Start background threads
        scheduler.start()
        logger.info("Successfully started background scheduler with registered jobs:")
        for job in scheduler.get_jobs():
            logger.info(f"  - Job ID: {job.id} | Name: {job.name} | Next Run: {job.next_run_time}")
        return True
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")
        return False

def stop_scheduler() -> bool:
    """
    Gracefully stops the background scheduler thread.
    """
    global scheduler
    if not scheduler.running:
        logger.warning("Scheduler is not currently running.")
        return False
        
    try:
        scheduler.shutdown(wait=True)
        logger.info("Successfully stopped background scheduler.")
        return True
    except Exception as e:
        logger.error(f"Failed to shutdown scheduler: {e}")
        return False

if __name__ == "__main__":
    print("Testing Reusable Scheduler Service...")
    
    # Define a helper function to simulate rapid logs for testing
    def test_rapid_job():
        print(f"[{datetime.now(timezone.utc).strftime('%H:%M:%S')}] Test Job Fired: Simulating rapid scheduler triggers.")

    try:
        # Start core jobs
        start_scheduler()
        
        # Register a temporary rapid interval job that triggers every 2 seconds for self-verification
        logger.info("Registering rapid test job (runs every 2 seconds)...")
        scheduler.add_job(
            test_rapid_job,
            "interval",
            seconds=2,
            id="test_rapid_job"
        )
        
        # Sleep for 5 seconds to let the test job fire twice
        print("Sleeping for 5 seconds to observe background triggers...")
        time.sleep(5)
        
        # Gracefully stop the scheduler
        print("Shutting down background scheduler...")
        stop_scheduler()
        print("Verification Test Completed!")
    except Exception as e:
        print(f"Scheduler Test Failed: {e}")
        sys.exit(1)
