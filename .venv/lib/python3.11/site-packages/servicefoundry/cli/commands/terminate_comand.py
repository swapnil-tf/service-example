import rich_click as click

from servicefoundry.cli.config import CliConfig
from servicefoundry.cli.const import COMMAND_CLS, GROUP_CLS
from servicefoundry.cli.display_util import print_entity_obj, print_json
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.lib.dao import application as application_lib


@click.group(name="terminate", cls=GROUP_CLS)
def terminate_command():
    """
    Terminate the job
    """
    pass


@click.command(name="job", cls=COMMAND_CLS, help="Terminate the Job")
@click.option(
    "--job-fqn",
    "--job_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the Job",
    required=True,
)
@click.option(
    "--job-run-name",
    "--job_run_name",
    type=click.STRING,
    default=None,
    help="Run name of the job",
    required=True,
)
@handle_exception_wrapper
def terminate_job_run(job_fqn, job_run_name):
    job_run = application_lib.terminate_job_run(
        application_fqn=job_fqn, job_run_name=job_run_name
    )
    print_json(data=job_run)


def get_terminate_command():
    terminate_command.add_command(terminate_job_run)
    return terminate_command
