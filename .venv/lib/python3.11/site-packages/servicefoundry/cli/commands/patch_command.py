import subprocess
from typing import Optional

import rich_click as click

from servicefoundry.cli.const import GROUP_CLS
from servicefoundry.cli.util import handle_exception_wrapper
from servicefoundry.io.rich_output_callback import RichOutputCallBack


@click.group(
    name="patch",
    cls=GROUP_CLS,
    invoke_without_command=True,
    help="Patch parts of servicefoundry.yaml file",
)
@click.option(
    "-f",
    "--file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    default="./servicefoundry.yaml",
    help="Path to servicefoundry.yaml file",
    show_default=True,
)
@click.option(
    "--filter",
    type=click.STRING,
    required=True,
    help="`yq` filter",
)
@click.option(
    "-o",
    "--output-file",
    type=click.Path(exists=False, writable=True, resolve_path=True),
    help="Path to yaml file to redirect the output",
    show_default=True,
)
@click.option(
    "-I",
    "--indent",
    default=4,
    type=click.INT,
    help="Indent level for output",
    show_default=True,
)
@handle_exception_wrapper
def patch_command(
    file: str, filter: str, output_file: Optional[str], indent: int
) -> None:
    yq_command = [
        "yq",
        "--output-format",
        "yaml",
        "--indent",
        str(indent),
        filter,
        file,
    ]
    if output_file:
        with open(output_file, "w") as fd:
            subprocess.run(yq_command, stdout=fd)
    else:
        p = subprocess.run(yq_command, stdout=subprocess.PIPE)
        output = p.stdout.decode("UTF-8")
        callback = RichOutputCallBack()
        callback.print_line(output)


def get_patch_command():
    return patch_command
