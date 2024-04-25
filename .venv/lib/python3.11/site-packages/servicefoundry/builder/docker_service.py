import os
import shlex
import subprocess
import sys
from typing import Any, Dict, List, Optional

import docker
from rich.console import Console

from servicefoundry.lib.clients.shell_client import Shell
from servicefoundry.logger import logger
from servicefoundry.pydantic_v1 import BaseModel

__all__ = [
    "build_docker_image",
    "push_docker_image",
    "pull_docker_image",
    "push_docker_image_with_latest_tag",
    "env_has_docker",
]


def _get_build_args_string(build_args: Optional[Dict[str, str]] = None) -> str:
    if not build_args:
        return None
    result = []
    for param, value in build_args.items():
        result.extend(["--build-arg", f"{param.strip()}={value}"])
    return result


def _get_docker_client():
    try:
        return docker.from_env()
    except Exception as ex:
        raise Exception("Could not connect to Docker") from ex


def env_has_docker():
    try:
        _get_docker_client()
        return True
    except Exception as ex:
        return False


# this is required since push does throw an error if it
# fails - so we have to parse the response logs to catch the error
# the other option is to run `docker login` as a subprocess, but it's
# not recommended to provide password to subprocess
def _catch_error_in_push(response: List[dict]):
    for line in response:
        if line.get("error") is not None:
            raise Exception(
                f'Failed to push to registry with message \'{line.get("error")}\''
            )


def _run_cmds(command: List[str]):
    console = Console(color_system=None, markup=False, soft_wrap=True)
    with subprocess.Popen(
        command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT
    ) as sp:
        for line in sp.stdout:
            console.print(line.decode("utf-8").strip())
        sp.communicate()
        if sp.returncode != None and sp.returncode != 0:
            raise Exception(f"Command: {command} failed")


def build_docker_image(
    path: str,
    tag: str,
    platform: str,
    dockerfile: str,
    extra_opts: Optional[List[str]] = None,
    build_args: Optional[Dict[str, str]] = None,
):
    use_depot = bool(os.environ.get("USE_DEPOT"))
    depot_project_id = os.environ.get("DEPOT_PROJECT_KEY")
    logger.info("Starting docker build...")
    if use_depot and depot_project_id:
        try:
            command = [
                "depot",
                "build",
                "--project",
                depot_project_id,
                "-f",
                dockerfile,
                "-t",
                tag,
                path,
            ]
            final_build_args = _get_build_args_string(build_args=build_args)
            if final_build_args:
                command.extend(final_build_args)
            command.append("--push")  # keep push at last
            Shell().execute_shell_command(command=command)
        except Exception as e:
            raise Exception("Error while building Docker image using Depot") from e
    else:
        try:
            # TODO (chiragjn): Maybe consider using client.images.build
            build_args_list = []
            if build_args:
                for k, v in build_args.items():
                    build_args_list += ["--build-arg", f"{k}={v}"]

            docker_build_cmd = [
                "docker",
                "build",
                "-t",
                tag,
                "-f",
                dockerfile,
                "--platform",
                platform,
            ]
            docker_build_cmd += [path]
            docker_build_cmd += build_args_list
            docker_build_cmd += extra_opts if extra_opts else []
            _run_cmds(docker_build_cmd)
        except Exception as e:
            raise Exception(f"Error while building Docker image: {e}") from e


def push_docker_image(
    image_uri: str,
    docker_login_username: str,
    docker_login_password: str,
):
    client = _get_docker_client()
    auth_config = {"username": docker_login_username, "password": docker_login_password}
    logger.info(f"Pushing {image_uri}")
    response = client.images.push(
        repository=image_uri, auth_config=auth_config, decode=True, stream=True
    )
    _catch_error_in_push(response=response)


def push_docker_image_with_latest_tag(
    image_uri: str,
    docker_login_username: str,
    docker_login_password: str,
):
    client = _get_docker_client()
    auth_config = {"username": docker_login_username, "password": docker_login_password}
    repository_without_tag, _ = image_uri.rsplit(":", 1)
    image = client.images.get(image_uri)
    image.tag(repository=repository_without_tag, tag="latest")

    logger.info(f"Pushing {repository_without_tag}:latest")
    response = client.images.push(
        repository=repository_without_tag,
        tag="latest",
        auth_config=auth_config,
        decode=True,
        stream=True,
    )
    _catch_error_in_push(response=response)


def pull_docker_image(
    image_uri: str,
    docker_login_username: str,
    docker_login_password: str,
):
    auth_config = {"username": docker_login_username, "password": docker_login_password}
    logger.info(f"Pulling cache image {image_uri}")
    _get_docker_client().images.pull(repository=image_uri, auth_config=auth_config)
