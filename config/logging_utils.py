"""Logging helpers: force log timestamps to IST regardless of the host timezone."""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class ISTFormatter(logging.Formatter):
    """Formatter that renders ``asctime`` in Asia/Kolkata local time."""

    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, IST)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()
