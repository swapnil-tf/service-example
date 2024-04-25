import re
from datetime import datetime, timedelta, timezone

from dateutil import parser
from dateutil.tz import tzlocal

from servicefoundry.logger import logger

time_duration_regex = re.compile("^[0-9]+[smhd]$")

granularity_timedelta = {
    "s": timedelta(seconds=1),
    "m": timedelta(minutes=1),
    "h": timedelta(hours=1),
    "d": timedelta(days=1),
}


def get_timestamp_from_timestamp_or_duration(time_or_duration: str):
    """
    Returns timestamp in milliseconds
    """
    if time_duration_regex.match(time_or_duration):
        number = int(time_or_duration[:-1])
        granularity = time_or_duration[-1]
        current_time = datetime.now(timezone.utc)
        required_time = current_time - granularity_timedelta[granularity] * number
        return required_time.timestamp() * 1000
    else:
        logger.debug(
            f"Cannot parse: {time_or_duration} as duration, regex match failed"
        )
        try:
            date_time_obj = parser.parse(time_or_duration)
        except ValueError as e:
            logger.debug(f"Value not a valid timestamp or duration: {time_or_duration}")
            raise ValueError(
                f"Value not a valid timestamp or duration: {time_or_duration}"
            )
        if not date_time_obj.tzinfo:
            date_time_obj = date_time_obj.replace(tzinfo=tzlocal())
        date_time_obj = date_time_obj.astimezone(timezone.utc)
        return date_time_obj.timestamp() * 1000
