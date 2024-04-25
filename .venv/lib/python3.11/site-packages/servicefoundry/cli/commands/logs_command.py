from datetime import datetime
from typing import Optional

import rich_click as click
from dateutil.tz import tzlocal

from servicefoundry.cli.const import COMMAND_CLS
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.io.rich_output_callback import RichOutputCallBack
from servicefoundry.lib.clients.service_foundry_client import (
    ServiceFoundryServiceClient,
)
from servicefoundry.lib.logs_utils import get_timestamp_from_timestamp_or_duration
from servicefoundry.lib.util import get_deployment_fqn_from_application_fqn
from servicefoundry.logger import logger


@click.command(name="logs", cls=COMMAND_CLS)
@click.option(
    "--application-fqn",
    type=click.STRING,
    help="FQN of the application",
    required=True,
)
@click.option(
    "--job-run-name",
    "--job_run_name",
    type=click.STRING,
    default=None,
    help="Run name of the job (if application is a job)",
)
@click.option(
    "--version",
    type=click.INT,
    help="Version number of the application deployment",
    default=None,
)
@click.option(
    "--since",
    type=click.STRING,
    help="Show logs since timestamp (e.g.2013-01-02T13:23:37Z) or relative (e.g. 42m for 42 minutes)",
    default="2h",
)
@click.option(
    "--until",
    type=click.STRING,
    help="Show logs until timestamp (e.g.2013-01-02T13:23:37Z) or relative (e.g. 42m for 42 minutes)",
    default=None,
)
@click.option(
    "-n", "--tail", type=click.INT, help="Number of logs to tail", default=None
)
@click.option("-f", "--follow", help="Follow log output", is_flag=True, default=False)
@handle_exception_wrapper
def logs_command(
    application_fqn: str,
    job_run_name: Optional[str],
    version: Optional[int],
    since: str,
    until: Optional[str],
    tail: Optional[int],
    follow: bool,
) -> None:
    """
    Get logs for Application
    """
    start_ts = get_timestamp_from_timestamp_or_duration(since)
    end_ts = (
        get_timestamp_from_timestamp_or_duration(until)
        if until
        else datetime.now().timestamp() * 1000
    )

    output_hook = RichOutputCallBack()
    tfs_client = ServiceFoundryServiceClient()

    if version:
        deployment_fqn = get_deployment_fqn_from_application_fqn(
            application_fqn=application_fqn, version=version
        )
        deployment_fqn_response = tfs_client.get_deployment_info_by_fqn(deployment_fqn)
        workspace_id, application_id, deployment_id = (
            deployment_fqn_response.workspaceId,
            deployment_fqn_response.applicationId,
            deployment_fqn_response.deploymentId,
        )
    else:
        app_fqn_response = tfs_client.get_application_info_by_fqn(application_fqn)
        workspace_id, application_id, deployment_id = (
            app_fqn_response.workspaceId,
            app_fqn_response.applicationId,
            None,
        )

    if until:
        logger.info(
            "Fetching logs from %s to %s for application fqn: %s",
            datetime.fromtimestamp(start_ts / 1000, tzlocal()).isoformat(),
            datetime.fromtimestamp(end_ts / 1000, tzlocal()).isoformat(),
            application_fqn,
        )
    else:
        logger.info(
            "Fetching logs from %s for application fqn: %s",
            datetime.fromtimestamp(start_ts / 1000, tzlocal()).isoformat(),
            application_fqn,
        )

    if until or not follow:
        tfs_client.fetch_deployment_logs(
            workspace_id=workspace_id,
            application_id=application_id,
            deployment_id=deployment_id,
            job_run_name=job_run_name,
            start_ts=start_ts,
            end_ts=end_ts,
            limit=tail,
            callback=output_hook,
        )
    else:
        tfs_client.poll_logs_for_deployment(
            workspace_id=workspace_id,
            application_id=application_id,
            deployment_id=deployment_id,
            job_run_name=job_run_name,
            start_ts=start_ts,
            limit=tail,
            poll_interval_seconds=5,
            callback=output_hook,
        )


def get_logs_command():
    return logs_command
