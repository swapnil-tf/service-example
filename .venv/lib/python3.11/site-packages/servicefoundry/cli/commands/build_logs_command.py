from typing import Optional

import rich_click as click

from servicefoundry.cli.const import COMMAND_CLS
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.io.rich_output_callback import RichOutputCallBack
from servicefoundry.lib.clients.service_foundry_client import (
    ServiceFoundryServiceClient,
)
from servicefoundry.lib.util import get_deployment_fqn_from_application_fqn
from servicefoundry.logger import logger


@click.command(name="build-logs", cls=COMMAND_CLS)
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    help="Application FQN",
    required=True,
)
@click.option(
    "--version",
    type=click.INT,
    help="Deployment version. If no deployment version "
    "given, logs will be fetched for the latest version",
)
@click.option("-f", "--follow", help="Follow log output", is_flag=True, default=False)
@handle_exception_wrapper
def build_logs_command(
    application_fqn: str,
    version: Optional[int],
    follow: bool,
) -> None:
    """
    Get build logs for application fqn and deployment version
    """
    output_hook = RichOutputCallBack()
    tfs_client = ServiceFoundryServiceClient()

    if not version:
        app_fqn_response = tfs_client.get_application_info_by_fqn(application_fqn)
        application_info = tfs_client.get_application_info(
            app_fqn_response.applicationId
        )
        version = application_info.lastVersion

    deployment_fqn = get_deployment_fqn_from_application_fqn(
        application_fqn=application_fqn, version=version
    )

    deployment_fqn_response = tfs_client.get_deployment_info_by_fqn(
        deployment_fqn=deployment_fqn
    )

    build_responses = tfs_client.get_deployment_build_response(
        application_id=deployment_fqn_response.applicationId,
        deployment_id=deployment_fqn_response.deploymentId,
    )

    if not build_responses:
        raise Exception(
            f"Unable to find a build version for application fqn {application_fqn} and version {version}"
        )

    build_response = build_responses[0]
    if not follow:
        tfs_client.fetch_build_logs(
            build_response=build_response,
            callback=output_hook,
        )
    else:
        try:
            logger.info(
                "You can press Ctrl + C to exit the tailing of build "
                "logs and deployment will continue on the server"
            )
            tfs_client.tail_build_logs(
                build_response=build_response,
                callback=output_hook,
                wait=True,
            )
        except KeyboardInterrupt:
            logger.info("Ctrl-C executed. The deployment will still continue.")


def get_build_logs_command():
    return build_logs_command
