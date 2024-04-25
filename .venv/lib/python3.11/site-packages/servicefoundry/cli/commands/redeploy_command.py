import rich_click as click

from servicefoundry.cli.const import COMMAND_CLS
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.lib.dao import application as application_lib


@click.command(name="redeploy", cls=COMMAND_CLS)
@click.option(
    "--application-fqn",
    type=click.STRING,
    default=None,
    help="Application fqn",
    required=True,
)
@click.option(
    "--version",
    type=click.STRING,
    default=None,
    help="Application deployment version",
    required=True,
)
@click.option(
    "--wait/--no-wait",
    is_flag=True,
    show_default=True,
    default=True,
    help="wait and tail the deployment progress",
)
@handle_exception_wrapper
def redeploy_command(application_fqn: str, version: int, wait: bool):
    """
    Redeploy specific version of an application
    """
    _deployment = application_lib.redeploy_application(
        application_fqn=application_fqn, version=version, wait=wait
    )


def get_redeploy_command():
    return redeploy_command
