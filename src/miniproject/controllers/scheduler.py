from datetime import datetime
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text

from miniproject.connections.db import engine

# Configured for Asia/Kolkata timezone
scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Kolkata"))


async def my_cron_job():
    """Daily cleanup job: removes expired subscriptions from the database."""
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    print(f"[Cron Job] Running daily cleanup for date: {today}")
    try:
        with engine.begin() as connection:
            data = connection.execute(
                text("""
                    DELETE FROM subscriptions 
                    WHERE end_date <= :today
                """),
                {"today": today},
            )
            print(f"[Cron Job] Cleaned up {data.rowcount} expired subscription(s)")
    except Exception as e:
        print(f"[Cron Job Error] Failed to delete expired subscriptions: {e}")


def start_scheduler():
    """Starts the daily cron job running every day at midnight (00:00:00 Asia/Kolkata)."""
    if not scheduler.running:
        scheduler.add_job(
            my_cron_job,
            CronTrigger(hour=0, minute=0, timezone=ZoneInfo("Asia/Kolkata")),
            id="daily_job",
            replace_existing=True,
        )
        scheduler.start()
        print("[Scheduler] Started daily cron job scheduled for 00:00 Asia/Kolkata everyday")


def stop_scheduler():
    """Stops the scheduler gracefully on shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Stopped scheduler")
