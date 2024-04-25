import contextlib
import sys
from enum import Enum

import rich_click as click
import yaml
from rich.pretty import pprint

from servicefoundry.cli.config import CliConfig
from servicefoundry.cli.console import console
from servicefoundry.cli.const import COMMAND_CLS, GROUP_CLS
from servicefoundry.cli.display_util import print_entity_obj, print_json
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.lib.dao import application as application_lib
from servicefoundry.lib.dao import version as version_lib
from servicefoundry.lib.dao import workspace as workspace_lib
from servicefoundry.lib.util import is_experimental_env_set

# TODO (chiragjn): --json should disable all non json console prints


@click.group(name="get", cls=GROUP_CLS)
def get_command():
    # TODO (chiragjn): Figure out a way to update supported resources based on ENABLE_* flags
    """
    Get Truefoundry resources

    \b
    Supported resources:
    - Workspace
    - Application
    - Application Version
    """
    pass


@click.command(name="workspace", cls=COMMAND_CLS, help="Get Workspace details")
@click.option(
    "-w",
    "--workspace-fqn",
    "--workspace_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the Workspace",
    required=True,
)
@handle_exception_wrapper
def get_workspace(workspace_fqn):
    workspace = workspace_lib.get_workspace_by_fqn(workspace_fqn=workspace_fqn)
    if CliConfig.get("json"):
        print_json(data=workspace.dict())
    else:
        print_entity_obj("Workspace", workspace)


@click.command(name="application", cls=COMMAND_CLS, help="Get Application details")
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the application",
    required=True,
)
@handle_exception_wrapper
def get_application(application_fqn):
    application = application_lib.get_application(application_fqn=application_fqn)
    if CliConfig.get("json"):
        print_json(data=application.dict())
    else:
        print_entity_obj(
            "Application",
            application,
        )


@click.command(
    name="application-version", cls=COMMAND_CLS, help="Get Application Version details"
)
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the application",
    required=True,
)
@click.option(
    "--version",
    type=click.STRING,
    default=None,
    help="Version number of the application deployment",
    required=True,
)
@handle_exception_wrapper
def get_version(application_fqn, version):
    version = version_lib.get_version(application_fqn=application_fqn, version=version)
    if CliConfig.get("json"):
        print_json(data=version.dict())
    else:
        print_entity_obj("Version", version)


@click.command(
    name="spec", cls=COMMAND_CLS, help="Get YAML/Python Spec for an Application Version"
)
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the application",
    required=True,
)
@click.option(
    "--version",
    type=click.STRING,
    default=None,
    help="Version number of the application deployment",
    required=True,
)
@click.option(
    "-o",
    "--output",
    type=click.Choice(
        [
            "yml",
            "yaml",
            "json",
            "py",
            "python",
        ]
    ),
    default="yaml",
    help="Output format for the spec",
    required=False,
)
@handle_exception_wrapper
def get_spec(application_fqn, version, output):
    version = version_lib.get_version(application_fqn=application_fqn, version=version)
    if output in ["yml", "yaml"]:
        yaml.safe_dump(version.manifest.dict(), sys.stdout, indent=2)
    elif output in ["json"]:
        print_json(version.manifest.dict())
    elif output in ["py", "python"]:
        from servicefoundry.v2.lib.deployable_patched_models import Application

        manifest = version.manifest.dict()
        instance = Application.parse_obj(manifest).__root__

        # TODO (chiragjn): Can we somehow just enable `use_enum_values` on all Pydantic classes?

        @contextlib.contextmanager
        def _monkey_patch_enum_repr():
            def new_repr(self):
                # return "%r" % (self._value_)
                return "%s.%s" % (self.__class__.__name__, self._name_)

            enum_subclasses = [
                es
                for es in Enum.__subclasses__()
                if es.__module__.startswith("servicefoundry.")
            ]
            original_reprs = []
            for es in enum_subclasses:
                original_reprs.append(es)
                es.__repr__ = new_repr

            yield

            for es, og_repr in zip(enum_subclasses, original_reprs):
                es.__repr__ = og_repr

        with _monkey_patch_enum_repr():
            pprint(
                instance,
                indent_guides=False,
                max_length=88,
                expand_all=True,
                console=console,
            )


@click.command(name="job-run", cls=COMMAND_CLS, help="Get Job Run")
@click.option(
    "--application-fqn",
    "--application_fqn",
    type=click.STRING,
    default=None,
    help="FQN of the application",
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
def get_job_run(application_fqn, job_run_name):
    job_run = application_lib.get_job_run(
        application_fqn=application_fqn, job_run_name=job_run_name
    )
    if CliConfig.get("json"):
        print_json(data=job_run.dict())
    else:
        print_entity_obj("Job Run", job_run)


def get_get_command():
    get_command.add_command(get_workspace)
    get_command.add_command(get_application)
    get_command.add_command(get_version)
    get_command.add_command(get_job_run)
    if is_experimental_env_set():
        get_command.add_command(get_spec)
    return get_command
