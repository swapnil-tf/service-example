import os

import rich_click as click

DISPLAY_DATETIME_FORMAT = "%d %b %Y %H:%M:%S %Z"

# TODO (chiragjn): This is a hacky solution used while generating docs. Although
#                  this does not cover cases where custom cls class already inherited from rich_click classes
#                  is being used
RICH_CLICK_DISABLED = os.getenv("RICH_CLICK_DISABLED")
GROUP_CLS = click.Group if RICH_CLICK_DISABLED else click.RichGroup
COMMAND_CLS = click.Command if RICH_CLICK_DISABLED else click.RichCommand
