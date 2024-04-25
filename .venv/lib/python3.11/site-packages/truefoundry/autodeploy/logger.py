import logging

from rich.logging import RichHandler

from truefoundry.autodeploy.constants import DEBUG

logger = logging.getLogger("autodeploy")

level = logging.DEBUG if DEBUG else logging.NOTSET
handler = RichHandler(level=level, show_path=False)
handler.setLevel(level)
logger.addHandler(handler)
logger.setLevel(level)
