import json
import os
import sys

import rich_click as click
import yaml
from click import UsageError
from click.exceptions import ClickException
from servicefoundry.cli.const import GROUP_CLS
from servicefoundry.lib.dao import application as application_lib

from truefoundry.autodeploy.exception import GitBinaryNotFoundException

GIT_BINARY = True

try:
    from truefoundry.autodeploy.cli import cli as autodeploy_cli
except GitBinaryNotFoundException:
    GIT_BINARY = False

default_file = "default"


def _get_yaml_file():
    files = ["truefoundry.yaml", "servicefoundry.yaml"]
    for file in files:
        if os.path.exists(file):
            return file
    return None


@click.group(
    name="deploy",
    cls=GROUP_CLS,
    invoke_without_command=True,
    help="Deploy application to Truefoundry",
)
@click.option(
    "-f",
    "--file",
    type=click.STRING,
    default=default_file,
    help="Path to truefoundry.yaml file",
    show_default=False,
)
@click.option(
    "-w",
    "--workspace-fqn",
    "--workspace_fqn",
    required=True,
    help="FQN of the Workspace to deploy to",
)
@click.option(
    "--wait/--no-wait",
    "--wait/--no_wait",
    is_flag=True,
    show_default=True,
    default=True,
    help="Wait and tail the deployment progress",
)
def deploy_v2_command(file: str, workspace_fqn: str, wait: bool):
    from servicefoundry.lib.auth.servicefoundry_session import ServiceFoundrySession
    from servicefoundry.v2.lib.deployable_patched_models import Application

    try:
        _ = ServiceFoundrySession()
    except Exception as e:
        raise ClickException(message=str(e)) from e

    if file != default_file and not os.path.exists(file):
        raise UsageError(
            f"The file {file} does not exist. Please check the file path and try again."
        )

    file = _get_yaml_file()

    if file is None:
        click.echo(
            click.style(
                "We did not find any truefoundry.yaml or servicefoundry.yaml at the root path.",
                fg="red",
            ),
            color=True,
        )

        if not sys.stdout.isatty():
            click.echo(
                click.style(
                    'Please create a truefoundry.yaml or pass the file name with "--file file_name"',
                    fg="yellow",
                ),
                color=True,
            )
            sys.exit(1)

        click.echo(
            click.style(
                'We will be using TrueFoundry AI to build your project.\nIf you wish to proceed without TrueFoundry AI,\nyou need to either have a truefoundry.yaml file in your project root or\npass the path to a yaml file using the "--file file_name" option.',
                fg="yellow",
            ),
        )

        if GIT_BINARY:
            autodeploy_cli(
                project_root_path=".", deploy=True, workspace_fqn=workspace_fqn
            )
        else:
            raise UsageError(
                "We cannot find the 'git' command. We use Git to track changes made while automatically building your project. Please install Git to use this feature or manually create a 'truefoundry.yaml' file."
            )
    else:
        with open(file, "r") as f:
            application_definition = yaml.safe_load(f)

        application = Application.parse_obj(application_definition)
        application.deploy(workspace_fqn=workspace_fqn, wait=wait)


@click.group(
    name="patch-application",
    cls=GROUP_CLS,
    invoke_without_command=True,
    help="Deploy application with patches to Truefoundry",
)
@click.option(
    "-f",
    "--patch-file",
    "--patch_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to yaml patch file",
    show_default=True,
)
@click.option(
    "-p",
    "--patch",
    type=click.STRING,
    help="Patch in JSON format provided as a string.",
    show_default=True,
)
@click.option(
    "-a",
    "--application_fqn",
    "--application-fqn",
    type=click.STRING,
    required=True,
    help="FQN of the Application to patch and deploy",
)
@click.option(
    "--wait/--no-wait",
    "--wait/--no_wait",
    is_flag=True,
    show_default=True,
    default=True,
    help="Wait and tail the deployment progress",
)
def deploy_patch_v2_command(
    patch_file: str, application_fqn: str, patch: str, wait: bool
):
    from servicefoundry.v2.lib.deployable_patched_models import Application

    manifest_patch_obj = None
    if not patch_file and not patch:
        raise Exception("You need to either provide --file or --patch.")
    elif patch and patch_file:
        raise Exception("You can only provide one of --file and --patch")
    elif patch:
        try:
            manifest_patch_obj = json.loads(patch)
        except json.decoder.JSONDecodeError as e:
            raise Exception("Invalid JSON provided as --patch") from e
    elif patch_file:
        with open(patch_file, "r") as f:
            manifest_patch_obj = yaml.safe_load(f)

    if not manifest_patch_obj or not isinstance(manifest_patch_obj, dict):
        raise Exception("Invalid patch, aborting deployment.")

    tfy_application = application_lib.get_application(application_fqn=application_fqn)
    patched_application_obj = application_lib.get_patched_application_definition(
        application=tfy_application, manifest_patch=manifest_patch_obj
    )

    application = Application.parse_obj(patched_application_obj)
    application.deploy(workspace_fqn=tfy_application.workspace.fqn, wait=wait)
