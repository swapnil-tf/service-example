from typing import Optional

import rich_click as click

from servicefoundry.cli.const import COMMAND_CLS, GROUP_CLS
from servicefoundry.cli.display_util import print_obj
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.lib.dao import workspace as workspace_lib


@click.group(name="create", cls=GROUP_CLS)
def create_command():
    # TODO (chiragjn): Figure out a way to update supported resources based on ENABLE_* flags
    """
    Create Truefoundry resources

    \b
    Supported resources:
    - Workspace
    """
    pass


@click.command(name="workspace", cls=COMMAND_CLS, help="Create a new Workspace")
@click.argument("name", type=click.STRING)
@click.option(
    "-c",
    "--cluster-name",
    "--cluster_name",
    type=click.STRING,
    required=True,
    help="Cluster to create this workspace in",
)
@click.option(
    "--cpu-limit",
    "--cpu_limit",
    type=click.FLOAT,
    default=None,
    help="CPU Limit",
)
@click.option(
    "--memory-limit",
    "--memory_limit",
    type=click.INT,
    default=None,
    help="Memory Limit in MB",
)
@click.option(
    "--ephemeral-storage-limit",
    "--ephemeral_storage_limit",
    type=click.INT,
    default=None,
    help="Ephemeral Storage Limit in GB",
)
@handle_exception_wrapper
def create_workspace(
    name: str,
    cluster_name: str,
    cpu_limit: Optional[float],
    memory_limit: Optional[int],
    ephemeral_storage_limit: Optional[int],
):
    workspace = workspace_lib.create_workspace(
        name=name,
        cpu_limit=cpu_limit,
        memory_limit=memory_limit,
        ephemeral_storage_limit=ephemeral_storage_limit,
        cluster_name=cluster_name,
    )
    print_obj("Workspace", workspace.dict())


def get_create_command():
    create_command.add_command(create_workspace)
    return create_command
