from typing import Optional

from servicefoundry.cli.console import console
from servicefoundry.lib.clients.service_foundry_client import (
    ServiceFoundryServiceClient,
)
from servicefoundry.lib.messages import PROMPT_CREATING_NEW_WORKSPACE
from servicefoundry.lib.model.entity import Workspace, WorkspaceResources
from servicefoundry.logger import logger


def create_workspace(
    name: str,
    cluster_name: str,
    cpu_limit: Optional[float] = None,
    memory_limit: Optional[int] = None,
    ephemeral_storage_limit: Optional[int] = None,
    client: Optional[ServiceFoundryServiceClient] = None,
) -> Workspace:
    client = client or ServiceFoundryServiceClient()

    workspace_resources = WorkspaceResources(
        cpu_limit=cpu_limit,
        memory_limit=memory_limit,
        ephemeral_storage_limit=ephemeral_storage_limit,
    )

    with console.status(PROMPT_CREATING_NEW_WORKSPACE.format(name), spinner="dots"):
        workspace = client.create_workspace(
            workspace_name=name,
            cluster_name=cluster_name,
            resources=workspace_resources,
        )

    url = f"{client.base_url.strip('/')}/workspaces"
    logger.info(
        "You can find your workspace: '%s' on the dashboard: %s", workspace.name, url
    )

    return workspace


def list_workspaces(
    cluster_name: Optional[str] = None,
    client: Optional[ServiceFoundryServiceClient] = None,
):
    client = client or ServiceFoundryServiceClient()
    workspaces = client.list_workspaces(cluster_id=cluster_name)
    return workspaces


def get_workspace_by_fqn(
    workspace_fqn: str,
    client: Optional[ServiceFoundryServiceClient] = None,
) -> Workspace:
    client = client or ServiceFoundryServiceClient()
    workspaces = client.get_workspace_by_fqn(workspace_fqn=workspace_fqn)
    if len(workspaces) == 0:
        raise ValueError(f"Workspace with FQN {workspace_fqn!r} does not exist.")
    workspace = workspaces[0]
    return workspace


def delete_workspace(
    workspace_fqn: str,
    client: Optional[ServiceFoundryServiceClient] = None,
) -> Workspace:
    client = client or ServiceFoundryServiceClient()
    workspace = client.get_id_from_fqn(fqn=workspace_fqn, fqn_type="workspace")
    deleted_workspace = client.remove_workspace(workspace_id=workspace["workspaceId"])
    return deleted_workspace
