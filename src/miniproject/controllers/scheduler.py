from apscheduler.schedulers.asyncio import AsyncIOScheduler
from miniproject.connections.db import engine

from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger

from datetime import datetime , timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status, Body
from sqlalchemy import text

scheduler = AsyncIOScheduler(
    timezone="Asia/Kolkata"
)

async def my_cron_job():
    print("executed")
    with engine.begin() as connection:
        data=connection.execute(
            text("""
                    delete from subscriptions where end_date=:today
                """),
                {"today": datetime.now(ZoneInfo("Asia/Kolkata")).date()},
        )
        print(data.rowcount, "rows deleted from subscriptions table")


def start_scheduler():
    scheduler.add_job(
        my_cron_job,
        IntervalTrigger(seconds=5453),
        id="daily_job",
        replace_existing=True
    )

    scheduler.start()

def stop_scheduler():
    scheduler.shutdown(wait=False)