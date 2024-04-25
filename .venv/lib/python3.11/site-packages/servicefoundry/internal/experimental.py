# This is meant to hold experimental features - stuff that is provisional and allowed to break
# DO NOT import stuff from here globally. Always import it locally restricted to as smaller scope as possible
# Always guard the imports under servicefoundry.lib.util.is_experimental_env_set
import functools

from servicefoundry.logger import logger


def _warn_on_call(fn):
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        logger.warning(
            f"Warning: This feature {fn.__name__} is in experimental stage. "
            f"As such there is no guarantees this will be maintained with backward compatibility "
            f"or even available moving forward"
        )
        return fn(*args, **kwargs)

    return wrapper
