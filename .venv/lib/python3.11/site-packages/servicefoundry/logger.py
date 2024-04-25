# https://docs.python.org/3/howto/logging.html#library-config
import logging

from rich.logging import RichHandler

logger = logging.getLogger("servicefoundry")


def add_cli_handler(level: int = logging.INFO, show_path=False):
    # TODO (chiragjn): Probably don't use rich handler, it adds hard breaks
    # See: https://github.com/Textualize/rich/discussions/344
    # Maybe try: https://github.com/pycontribs/enrich/blob/main/src/enrich/logging.py
    # or simpler override of logging.Handler with console.print(rich.Text("..."))
    handler = RichHandler(level=level, show_path=show_path)
    handler.setLevel(level)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
