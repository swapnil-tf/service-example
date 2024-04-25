import os
import time
from typing import Any, Callable, Generator, Optional

from servicefoundry.lib.const import DEFAULT_BASE_URL, HOST_ENV_NAME
from servicefoundry.lib.exceptions import BadRequestException


def request_handling(res):
    try:
        status_code = res.status_code
    except Exception as ex:
        raise Exception("Unknown error occurred. Couldn't get status code.") from ex
    if 200 <= status_code <= 299:
        if res.content == b"":
            return None
        return res.json()
    if 400 <= status_code <= 499:
        try:
            message = str(res.json()["message"])
        except Exception:
            message = res
        raise BadRequestException(res.status_code, message)
    if 500 <= status_code <= 599:
        raise Exception(res.content)


def poll_for_function(
    func: Callable, poll_after_secs: int = 5, *args, **kwargs
) -> Generator[Any, None, None]:
    while True:
        yield func(*args, **kwargs)
        time.sleep(poll_after_secs)


def resolve_base_url(host: Optional[str] = None) -> str:
    if not host and not os.getenv(HOST_ENV_NAME):
        raise ValueError(
            f"Either `host` should be provided by --host <value>, or `{HOST_ENV_NAME}` env must be set"
        )
    return host or os.getenv(HOST_ENV_NAME)
