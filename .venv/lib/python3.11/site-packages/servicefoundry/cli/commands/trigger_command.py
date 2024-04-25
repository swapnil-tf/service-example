import json
from typing import Dict, Optional, Sequence

import rich_click as click
from click import ClickException

from servicefoundry.cli.const import COMMAND_CLS, GROUP_CLS
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.lib.dao import application


@click.group(name="trigger", cls=GROUP_CLS)
def trigger_command():
    """
    Trigger a Job asynchronously
    """
    pass


@click.command(
    name="job",
    cls=COMMAND_CLS,
    context_settings=dict(ignore_unknown_options=True, allow_extra_args=True),
)
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    required=True,
    help="FQN of the deployment of the Job. This can be found on the Job details page.",
)
@click.option("--command", type=click.STRING, required=False, help="Command to run")
@click.argument(
    "params",
    type=click.STRING,
    nargs=-1,
    required=False,
)
@handle_exception_wrapper
def trigger_job(application_fqn: str, command: Optional[Sequence[str]], params):
    """
    Trigger a Job on Truefoundry asynchronously

        [b]tfy trigger job --application-fqn "my-cluster:my-workspace:my-job"[/]

    \n
    Additionally, you can either pass `--command` or params (if defined in the spec)\n


    Passing a command:

        [b]tfy trigger job --application-fqn "my-cluster:my-workspace:my-job" --command "python run.py"[/]
    \n

    Passing params:

        [b]tfy trigger job --application-fqn "my-cluster:my-workspace:my-job" -- --param1_name param1_value --param2_name param2_value ...[/]
    """
    if params:
        params_dict = {}
        if len(params) % 2 != 0:
            raise ClickException(
                f"Found odd number of argument pairs: {params}. "
                "Perhaps you forgot to pass a value for one of the params? "
                "Job params should be passed in the "
                "format `--param1_name param1_value --param2_name param2_value ...`"
            )
        for i in range(0, len(params), 2):
            key = params[i]
            value = params[i + 1]
            if not key.startswith("--"):
                raise ClickException(
                    f"Got ambiguous argument {key!r} in params: {params}. "
                    f"Param names should be prefixed with '--' i.e. "
                    "Job params should be passed in the "
                    "format `--param1_name param1_value --param2_name param2_value ...`"
                )
            key = key.lstrip("-")
            params_dict[key] = value

    application.trigger_job(
        application_fqn=application_fqn, command=command, params=params
    )


def get_trigger_command():
    trigger_command.add_command(trigger_job)
    return trigger_command
