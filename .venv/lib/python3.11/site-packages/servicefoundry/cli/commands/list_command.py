import rich_click as click

from servicefoundry.cli.config import CliConfig
from servicefoundry.cli.const import COMMAND_CLS, GROUP_CLS
from servicefoundry.cli.display_util import print_entity_list, print_json
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.io.rich_output_callback import RichOutputCallBack
from servicefoundry.lib.dao import application as application_lib
from servicefoundry.lib.dao import version as version_lib
from servicefoundry.lib.dao import workspace as workspace_lib
from servicefoundry.lib.messages import (
    PROMPT_NO_APPLICATIONS,
    PROMPT_NO_VERSIONS,
    PROMPT_NO_WORKSPACES,
)

# TODO (chiragjn): --json should disable all non json console prints


@click.group(name="list", cls=GROUP_CLS)
def list_command():
    # TODO (chiragjn): Figure out a way to update supported resources based on ENABLE_* flags
    """
    List Truefoundry resources

    \b
    Supported resources:
    - Workspace
    - Application
    - Application Version
    """


@click.command(name="workspaces", cls=COMMAND_CLS, help="List Workspaces")
@click.option(
    "-c",
    "--cluster-name",
    "--cluster_name",
    type=click.STRING,
    default=None,
    help="Cluster name",
)
@handle_exception_wrapper
def list_workspaces(cluster_name):
    workspaces = workspace_lib.list_workspaces(
        cluster_name=cluster_name,
    )
    if not workspaces:
        output_hook = RichOutputCallBack()
        output_hook.print_line(PROMPT_NO_WORKSPACES)
    else:
        workspaces.sort(key=lambda s: s.createdAt, reverse=True)

    print_entity_list(
        "Workspaces",
        workspaces,
    )


@click.command(name="applications", cls=COMMAND_CLS, help="List Applications")
@click.option(
    "-w",
    "--workspace-fqn",
    "--workspace_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the Workspace",
)
@click.option(
    "--application-type",
    "--application_type",
    type=click.Choice(
        [
            "service",
            "job",
            "model-deployment",
            "volume",
            "notebook",
            "intercept",
            "helm",
            "all",
        ]
    ),
    default="all",
    help="Application Type",
)
@handle_exception_wrapper
def list_applications(workspace_fqn, application_type):
    applications = application_lib.list_applications(
        workspace_fqn=workspace_fqn, application_type=application_type
    )
    if not applications:
        output_hook = RichOutputCallBack()
        output_hook.print_line(PROMPT_NO_APPLICATIONS)
    else:
        applications.sort(key=lambda s: s.createdAt, reverse=True)

    print_entity_list(
        "Applications",
        applications,
    )


@click.command(
    name="application-versions", cls=COMMAND_CLS, help="List Application Versions"
)
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the application",
    required=True,
)
@handle_exception_wrapper
def list_versions(application_fqn):
    versions = version_lib.list_versions(
        application_fqn=application_fqn,
    )
    if not versions:
        output_hook = RichOutputCallBack()
        output_hook.print_line(PROMPT_NO_VERSIONS)
    else:
        versions.sort(key=lambda s: s.createdAt, reverse=True)

    print_entity_list(
        "Application Versions",
        versions,
    )


@click.command(name="job-run", cls=COMMAND_CLS, help="List Job Runs")
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the application",
    required=True,
)
@click.option(
    "--max-results",
    "--max_results",
    type=click.STRING,
    default=None,
    help="Maximum number of Runs to fetch",
)
@click.option(
    "--offset",
    type=click.STRING,
    default=None,
    help="Number of Runs to skip",
)
@handle_exception_wrapper
def list_job_runs(application_fqn, max_results, offset):
    job_runs = application_lib.list_job_runs(
        application_fqn=application_fqn, max_results=max_results, offset=offset
    )
    if CliConfig.get("json"):
        print_json(data=job_runs.dict())
    else:
        print_entity_list("Job Runs", job_runs)


def get_list_command():
    list_command.add_command(list_workspaces)
    list_command.add_command(list_applications)
    list_command.add_command(list_versions)
    list_command.add_command(list_job_runs)

    return list_command
