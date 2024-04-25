import logging
import sys

import rich_click as click
from servicefoundry import logger
from servicefoundry.cli.commands import (
    deploy_patch_v2_command,
    get_login_command,
    get_logout_command,
    get_patch_command,
)
from servicefoundry.cli.config import CliConfig
from servicefoundry.cli.const import GROUP_CLS
from servicefoundry.cli.util import setup_rich_click
from servicefoundry.lib.util import is_debug_env_set, is_experimental_env_set
from servicefoundry.version import __version__

from truefoundry.deploy.cli.deploy import deploy_v2_command

click.rich_click.USE_RICH_MARKUP = True


def _add_experimental_commands(cli):
    pass


def create_truefoundry_cli():
    """Generates CLI by combining all subcommands into a main CLI and returns in

    Returns:
        function: main CLI functions will all added sub-commands
    """
    cli = truefoundry_cli
    cli.add_command(get_login_command())
    # cli.add_command(get_get_command())
    # cli.add_command(get_list_command())
    # cli.add_command(get_delete_command())
    # cli.add_command(get_create_command())
    # cli.add_command(get_redeploy_command())
    cli.add_command(get_logout_command())
    # cli.add_command(get_build_command())
    cli.add_command(deploy_v2_command)
    cli.add_command(deploy_patch_v2_command)
    # cli.add_command(get_build_logs_command())
    # cli.add_command(get_logs_command())
    # cli.add_command(get_trigger_command())
    # cli.add_command(get_terminate_command())

    if not (sys.platform.startswith("win32") or sys.platform.startswith("cygwin")):
        cli.add_command(get_patch_command())

    if is_experimental_env_set():
        _add_experimental_commands(cli)
    return cli


CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])  # noqa: C408


@click.group(
    cls=GROUP_CLS, context_settings=CONTEXT_SETTINGS, invoke_without_command=True
)
@click.option(
    "--json",
    is_flag=True,
    help="Output entities in json format instead of formatted tables",
)
@click.option(
    "--debug",
    is_flag=True,
    default=is_debug_env_set,
    help="Set logging level to Debug. Can also be set using environment variable. E.g. SFY_DEBUG=1",
)
@click.version_option(__version__)
@click.pass_context
def truefoundry_cli(ctx, json, debug):
    """
    Truefoundry provides an easy way to deploy your services, jobs and models.
    \b

    To start, login to your Truefoundry account with [i]tfy login[/]

    Then start deploying with [i]tfy deploy[/]

    And more: [link=https://docs.truefoundry.com/docs]https://docs.truefoundry.com/docs[/]

    """
    setup_rich_click()
    # TODO (chiragjn): Change this to -o json|yaml|table|pager
    CliConfig.set("json", json)
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
    log_level = logging.INFO
    # no info logs while outputting json
    if json:
        log_level = logging.ERROR
    if debug:
        log_level = logging.DEBUG
    logger.add_cli_handler(level=log_level)
