import json

import rich_click as click

from servicefoundry import builder
from servicefoundry.cli.console import console
from servicefoundry.cli.const import GROUP_CLS
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.version import __version__ as servicefoundry_version


@click.group(
    name="build",
    cls=GROUP_CLS,
    invoke_without_command=True,
    help="Build docker image locally from Truefoundry spec",
    context_settings=dict(ignore_unknown_options=True, allow_interspersed_args=True),
)
@click.option(
    "--name",
    type=click.STRING,
    required=True,
    help="Name for the image being build - used as docker tag",
)
@click.option(
    "--build-config",
    "--build_config",
    type=click.STRING,
    required=True,
    help="Build part of the spec as a json spec",
)
@click.argument("extra_opts", nargs=-1, type=click.UNPROCESSED)
@handle_exception_wrapper
def build_command(name, build_config, extra_opts):
    if build_config:
        console.print(rf"\[build] Servicefoundry version: {servicefoundry_version}")
        builder.build(
            build_configuration=json.loads(build_config),
            tag=name,
            extra_opts=extra_opts,
        )


def get_build_command():
    return build_command
