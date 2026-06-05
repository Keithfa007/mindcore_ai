#!/usr/bin/env python3
"""
MindCore AI -- Shared scheduling utility for Upload-Post scheduled posting.

All pipelines import from here to calculate the exact UTC time
Upload-Post should fire. GitHub delay is irrelevant -- generation
happens at 2am Malta, posting fires at the configured time.

Slots:
  Female video : POST_HOUR_UTC = 17 --> 19:00 Malta (CEST) evening slot
  Male slot A  : 09:00 UTC --> 11:00 Malta (Sat/Sun morning)
  Male slot B  : 13:00 UTC --> 15:00 Malta (Sat/Sun afternoon)
  Carousel     : 11:00 UTC --> 13:00 Malta (daily lunchtime)
"""
from datetime import datetime, timedelta, timezone

# Female video posts at 7pm Malta every day
FEMALE_POST_HOUR_UTC = 17   # 19:00 Malta CEST

# Male video slot hours -- keyed by the UTC hour the cron fires
# Cron 00:00 UTC (2am Malta) = slot A -> post at 09:00 UTC = 11:00 Malta
# Cron 01:00 UTC (3am Malta) = slot B -> post at 13:00 UTC = 15:00 Malta
MALE_SLOT_HOURS = {0: 9, 1: 13}


def get_scheduled_post_time(post_hour_utc=None):
    """Return ISO-8601 UTC string for the next occurrence of post_hour_utc.

    If post_hour_utc is None, auto-detects the male slot from the current
    UTC hour using MALE_SLOT_HOURS (defaults to morning slot if no match).

    If the target time has already passed today, returns tomorrow's time.
    """
    now = datetime.now(timezone.utc)

    if post_hour_utc is None:
        post_hour_utc = MALE_SLOT_HOURS.get(now.hour, 9)
        slot = "MORNING (11am Malta)" if post_hour_utc == 9 else "AFTERNOON (3pm Malta)"
        print(f"  Male slot: {slot}")

    target = now.replace(hour=post_hour_utc, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)

    scheduled = target.strftime("%Y-%m-%dT%H:%M:%SZ")
    malta_hour = post_hour_utc + 2  # CEST offset
    print(f"  Scheduled: {scheduled} ({post_hour_utc:02d}:00 UTC = {malta_hour:02d}:00 Malta)")
    return scheduled
