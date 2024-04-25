import rich_click as click

from servicefoundry.cli.const import COMMAND_CLS
from servicefoundry.cli.util import (
    _prompt_if_no_value_and_supported,
    handle_exception_wrapper,
)
from servicefoundry.io.rich_output_callback import RichOutputCallBack
from servicefoundry.lib.const import HOST_ENV_NAME
from servicefoundry.lib.session import login


@click.command(name="login", cls=COMMAND_CLS)
@click.option("--relogin", type=click.BOOL, is_flag=True, default=False)
@click.option("--host", type=click.STRING, required=True, envvar=HOST_ENV_NAME)
@click.option(
    "--api-key",
    "--api_key",
    type=click.STRING,
    default=None,
    **_prompt_if_no_value_and_supported(prompt="API Key", hide_input=True),
)
@handle_exception_wrapper
def login_command(relogin: bool, host: str, api_key: str):
    """
    Login to Truefoundry
    """
    callback = RichOutputCallBack()
    login(api_key=api_key, host=host, relogin=relogin, output_hook=callback)


def get_login_command():
    return login_command
