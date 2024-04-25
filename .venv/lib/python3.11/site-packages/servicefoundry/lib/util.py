import os
import re
from typing import Union

from servicefoundry.lib.const import (
    SFY_DEBUG_ENV_KEY,
    SFY_EXPERIMENTAL_ENV_KEY,
    SFY_INTERNAL_ENV_KEY,
)


def is_debug_env_set() -> bool:
    return True if os.getenv(SFY_DEBUG_ENV_KEY) else False


def is_experimental_env_set() -> bool:
    # TODO (chiragjn): one of these need to be removed
    return (
        True
        if os.getenv(SFY_EXPERIMENTAL_ENV_KEY) or os.getenv(SFY_INTERNAL_ENV_KEY)
        else False
    )


def get_application_fqn_from_deployment_fqn(deployment_fqn: str) -> str:
    if not re.search(r":\d+$", deployment_fqn):
        raise ValueError(
            "Invalid `deployment_fqn` format. A deployment fqn is supposed to end with a version number"
        )
    application_fqn, _ = deployment_fqn.rsplit(":", 1)
    return application_fqn


def get_deployment_fqn_from_application_fqn(
    application_fqn: str, version: Union[str, int]
) -> str:
    return f"{application_fqn}:{version}"


def is_notebook():
    # https://stackoverflow.com/questions/15411967/how-can-i-check-if-code-is-executed-in-the-ipython-notebook
    try:
        # noinspection PyUnresolvedReferences
        shell = get_ipython().__class__
        if shell.__name__ == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        elif shell.__name__ == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        elif "google.colab" in str(shell):
            return True  # google colab notebook
        else:
            return False  # Other type (?)
    except NameError:
        return False  # Probably standard Python interpreter


def find_list_paths(data, parent_key="", sep="."):
    list_paths = []
    if isinstance(data, dict):
        for key, value in data.items():
            new_key = f"{parent_key}{sep}{key}" if parent_key else key
            list_paths.extend(find_list_paths(value, new_key, sep))
    elif isinstance(data, list):
        list_paths.append(parent_key)
        for i, value in enumerate(data):
            new_key = f"{parent_key}[{i}]"
            list_paths.extend(find_list_paths(value, new_key, sep))
    return list_paths
