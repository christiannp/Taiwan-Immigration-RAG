from apscheduler.schedulers.background import BackgroundScheduler
from backend.ingest import process_url
import time
import google.api_core.exceptions as g_exc

def safe_process(url):
    retries = 3
    for i in range(retries):
        try:
            process_url(url)
            return
        except g_exc.ResourceExhausted:
            time.sleep(2 ** i)  # exponential backoff
    print(f"Failed to process {url} after retries.")

def run_ingest():
    urls = [
        # ... same list of URLs as in ingest.py ...
    ]
    for url in urls:
        safe_process(url)

if __name__ == "__main__":
    scheduler = BackgroundScheduler()
    # Schedule daily at midnight
    scheduler.add_job(run_ingest, 'cron', hour=0, minute=0)
    scheduler.start()
    print("Scheduler started. Press Ctrl+C to exit.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        scheduler.shutdown()