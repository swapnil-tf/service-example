import rich_click as click

from servicefoundry.cli.config import CliConfig
from servicefoundry.cli.const import COMMAND_CLS, GROUP_CLS
from servicefoundry.cli.display_util import print_json
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.io.rich_output_callback import RichOutputCallBack
from servicefoundry.lib.dao import application as application_lib
from servicefoundry.lib.dao import workspace as workspace_lib
from servicefoundry.lib.messages import (
    PROMPT_DELETED_APPLICATION,
    PROMPT_DELETED_WORKSPACE,
)

# TODO (chiragjn): --json should disable all non json console prints


@click.group(name="delete", cls=GROUP_CLS)
def delete_command():
    """
    Delete Truefoundry resources

    \b
    Supported resources:
    - Workspace
    - Application
    """
    pass


@click.command(name="workspace", cls=COMMAND_CLS, help="Delete a Workspace")
@click.option(
    "-w",
    "--workspace-fqn",
    "--workspace_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the Workspace to delete",
    required=True,
)
@click.confirmation_option(prompt="Are you sure you want to delete this workspace?")
@handle_exception_wrapper
def delete_workspace(workspace_fqn):
    deleted_workspace = workspace_lib.delete_workspace(
        workspace_fqn=workspace_fqn,
    )
    output_hook = RichOutputCallBack()
    output_hook.print_line(PROMPT_DELETED_WORKSPACE.format(workspace_fqn))
    if CliConfig.get("json"):
        print_json(data=deleted_workspace.dict())


@click.command(name="application", cls=COMMAND_CLS, help="Delete an Application")
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the Application to delete",
    required=True,
)
@click.confirmation_option(prompt="Are you sure you want to delete this application?")
@handle_exception_wrapper
def delete_application(application_fqn):
    response = application_lib.delete_application(
        application_fqn=application_fqn,
    )
    output_hook = RichOutputCallBack()
    output_hook.print_line(PROMPT_DELETED_APPLICATION.format(application_fqn))
    if CliConfig.get("json"):
        print_json(data=response)


def get_delete_command():
    delete_command.add_command(delete_workspace)
    delete_command.add_command(delete_application)
    return delete_command
