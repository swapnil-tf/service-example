import shlex
from typing import Any, Dict, Optional, Sequence, Union

import servicefoundry.lib.dao.version as version_lib
from servicefoundry.lib.clients.service_foundry_client import (
    ServiceFoundryServiceClient,
)
from servicefoundry.lib.model.entity import Application, Deployment, TriggerJobResult
from servicefoundry.lib.util import (
    find_list_paths,
    get_application_fqn_from_deployment_fqn,
)
from servicefoundry.logger import logger
from servicefoundry.pydantic_v1 import utils as pydantic_v1_utils


def list_applications(
    application_type: str,
    workspace_fqn: Optional[str] = None,
    client: Optional[ServiceFoundryServiceClient] = None,
):
    client = client or ServiceFoundryServiceClient()
    if workspace_fqn:
        workspace = client.get_id_from_fqn(fqn=workspace_fqn, fqn_type="workspace")
        applications = client.list_applications(workspace_id=workspace["workspaceId"])
    else:
        applications = client.list_applications()

    if application_type != "all":
        applications = [
            application
            for application in applications
            if application.deployment.manifest.type == application_type
        ]
    return applications


def get_application(
    application_fqn: str,
    client: Optional[ServiceFoundryServiceClient] = None,
):
    client = client or ServiceFoundryServiceClient()
    application = client.get_id_from_fqn(fqn=application_fqn, fqn_type="app")
    application = client.get_application_info(
        application_id=application["applicationId"]
    )
    return application


def delete_application(
    application_fqn: str,
    client: Optional[ServiceFoundryServiceClient] = None,
) -> Dict[str, Any]:
    client = client or ServiceFoundryServiceClient()
    application = client.get_id_from_fqn(fqn=application_fqn, fqn_type="app")
    response = client.remove_application(application_id=application["applicationId"])
    return response


def redeploy_application(
    application_fqn: str,
    version: int,
    wait: bool,
    client: Optional[ServiceFoundryServiceClient] = None,
) -> Deployment:
    from servicefoundry.v2.lib.deployable_patched_models import Application

    client = client or ServiceFoundryServiceClient()

    deployment_info = version_lib.get_version(
        application_fqn=application_fqn, version=version
    )

    manifest = deployment_info.manifest.dict()

    application_id = deployment_info.applicationId
    application_info = client.get_application_info(application_id=application_id)
    workspace_fqn = application_info.workspace.fqn

    application = Application.parse_obj(manifest)
    deployment = application.deploy(workspace_fqn=workspace_fqn, wait=wait)
    return deployment


def list_job_runs(
    application_fqn: str,
    max_results: Optional[int] = None,
    offset: Optional[int] = None,
    client: Optional[ServiceFoundryServiceClient] = None,
):
    client = client or ServiceFoundryServiceClient()
    application = client.get_id_from_fqn(fqn=application_fqn, fqn_type="app")
    response = client.list_job_runs(
        application_id=application["applicationId"], limit=max_results, offset=offset
    )
    return response


def get_job_run(
    application_fqn: str,
    job_run_name: str,
    client: Optional[ServiceFoundryServiceClient] = None,
):
    client = client or ServiceFoundryServiceClient()
    application = client.get_id_from_fqn(fqn=application_fqn, fqn_type="app")
    response = client.get_job_run(
        application_id=application["applicationId"], job_run_name=job_run_name
    )
    return response


def trigger_job(
    application_fqn: str,
    component_name: str = None,
    command: Optional[Union[str, Sequence[str]]] = None,
    params: Optional[Dict[str, str]] = None,
) -> TriggerJobResult:
    """
    Trigger a Job on Truefoundry platform

    Args:
        application_fqn: Fully Qualified Name of the Deployed Job (without the version number)
        component_name: Name of the component to trigger the job on. Required in case of type `application`, defaults to `None`.
        command: command to run the job with, defaults to `None`. Can be a `str` or `List[str]`
            When `None`, the job is triggered with configured command at the time of deployment.
            When passed as a list, the command will be joined using `shlex.join`
        params: A dict mapping from parameter names (as defined in the job spec) to string values

    Returns:
        TriggerJobResult: metadata returning status of job trigger
    """
    if params and command:
        raise ValueError(
            "`command` and `params` arguments are mutually exclusive. Please pass only one of them"
        )

    try:
        # If user is passing in deployment fqn copied from UI, till we change the fqns on UI
        application_fqn = get_application_fqn_from_deployment_fqn(application_fqn)
        logger.warning(
            "Detected version number in `application_fqn`. "
            "Automatically discarding the version number. "
            f"This automatic conversion will be removed in future. "
            f"Please pass {application_fqn!r} as the value."
        )
    except ValueError:
        pass
    client = ServiceFoundryServiceClient()
    _application_info = client.get_application_info_by_fqn(
        application_fqn=application_fqn
    )
    application_info = client.get_application_info(
        application_id=_application_info.applicationId
    )
    command_str = ""
    message = ""
    if not params and not command:
        message = "Job triggered with pre-configured command"
    elif command:
        if not isinstance(command, str):
            command_str = shlex.join(command).strip()
        else:
            command_str = command.strip()
        message = f"Job triggered with command {command_str!r}"
    elif params:
        # Check if params has any non string values
        for key, value in params.items():
            if not isinstance(value, str):
                raise ValueError(
                    f"Invalid value {value!r} for key {key!r}. "
                    "Only string values are allowed for `params`"
                )
        command_str = ""
        message = f"Job triggered with params {params!r}"
    result = client.trigger_job(
        deployment_id=application_info.activeDeploymentId,
        component_name=component_name,
        command=command_str if command_str else None,
        params=params if params else None,
    )
    previous_runs_url = f"{client.base_url.strip('/')}/deployments/{application_info.id}?tab=previousRuns"
    logger.info(
        f"{message}.\n"
        f"You can check the status of your job run at {previous_runs_url}"
    )
    return result


def get_patched_application_definition(
    application: Application,
    manifest_patch: Dict[str, Any],
) -> Dict[str, Any]:
    # TODO: define ApplicationPatch type but for now
    # I am adding a manual check for name since name patch can
    # create a new application
    if (
        manifest_patch.get("name")
        and manifest_patch.get("name") != application.deployment.manifest.name
    ):
        raise Exception(
            f"Cannot change name of application from `{application.deployment.manifest.name}` to `{manifest_patch.get('name')}`"
        )

    patch_list_paths = find_list_paths(manifest_patch)

    for path in patch_list_paths:
        logger.warn(
            f"You are patching the value at {path}. Note that updating array-type objects will replace the entire object."
        )

    return pydantic_v1_utils.deep_update(
        application.deployment.manifest.dict(), manifest_patch
    )


def terminate_job_run(
    application_fqn: str,
    job_run_name: str,
):
    try:
        application_fqn = get_application_fqn_from_deployment_fqn(application_fqn)
        logger.warning(
            "Detected version number in `application_fqn`. "
            "Automatically discarding the version number. "
            f"This automatic conversion will be removed in future. "
            f"Please pass {application_fqn!r} as the value."
        )
    except ValueError:
        pass
    client = ServiceFoundryServiceClient()
    _application_info = client.get_application_info_by_fqn(
        application_fqn=application_fqn
    )
    application_info = client.get_application_info(
        application_id=_application_info.applicationId
    )

    response = client.terminate_job_run(
        deployment_id=application_info.activeDeploymentId,
        job_run_name=job_run_name,
    )
    return response
