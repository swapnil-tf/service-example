from typing import Optional

from servicefoundry.lib import session


def login(
    host: Optional[str] = None, api_key: Optional[str] = None, relogin: bool = False
):
    session.login(api_key=api_key, relogin=relogin, host=host)
