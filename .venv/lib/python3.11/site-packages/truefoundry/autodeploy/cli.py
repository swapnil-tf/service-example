import logging
import os
import re
import sys
from typing import Dict, Optional

import click
import docker
import inquirer
from dotenv import dotenv_values

from truefoundry.autodeploy.exception import GitBinaryNotFoundException

try:
    from git import GitCommandError, Repo
    from git.exc import InvalidGitRepositoryError
except ImportError as ex:
    raise GitBinaryNotFoundException from ex

import requests
from click.exceptions import ClickException
from openai import OpenAI
from rich.console import Console
from rich.prompt import Prompt
from rich.status import Status
from servicefoundry import Build, DockerFileBuild, Job, LocalSource, Port, Service
from servicefoundry.cli.const import COMMAND_CLS
from servicefoundry.lib.auth.servicefoundry_session import ServiceFoundrySession

from truefoundry.autodeploy.agents.developer import Developer
from truefoundry.autodeploy.agents.project_identifier import (
    ComponentType,
    ProjectIdentifier,
)
from truefoundry.autodeploy.agents.tester import Tester
from truefoundry.autodeploy.constants import (
    ABOUT_AUTODEPLOY,
    AUTODEPLOY_INTRO_MESSAGE,
    AUTODEPLOY_OPENAI_API_KEY,
    AUTODEPLOY_OPENAI_BASE_URL,
    AUTODEPLOY_TFY_BASE_URL,
)
from truefoundry.autodeploy.tools.ask import AskQuestion
from truefoundry.autodeploy.tools.commit import CommitConfirmation
from truefoundry.autodeploy.tools.docker_run import DockerRun, DockerRunLog


def _get_openai_client() -> OpenAI:
    if AUTODEPLOY_OPENAI_BASE_URL is not None and AUTODEPLOY_OPENAI_API_KEY is not None:
        return OpenAI(
            api_key=AUTODEPLOY_OPENAI_API_KEY, base_url=AUTODEPLOY_OPENAI_BASE_URL
        )
    try:
        session = ServiceFoundrySession()
        resp = requests.get(
            f"{AUTODEPLOY_TFY_BASE_URL}/api/svc/v1/llm-gateway/access-details",
            headers={
                "Authorization": f"Bearer {session.access_token}",
            },
        )
        resp.raise_for_status()
        resp = resp.json()
        return OpenAI(api_key=resp["jwtToken"], base_url=resp["inferenceBaseURL"])
    except requests.exceptions.HTTPError as http_error:
        raise ClickException(
            f"An error occurred while connecting to the Truefoundry server.\nThe server responded with status code {http_error.response.status_code}."
        ) from http_error
    except Exception as e:
        raise ClickException(message=str(e)) from e


def deploy_component(
    workspace_fqn: str,
    project_root_path: str,
    dockerfile_path: str,
    component_type: ComponentType,
    name: str,
    env: Dict,
    command: Optional[str] = None,
    port: Optional[int] = None,
):
    logging.basicConfig(level=logging.INFO)

    if not os.path.exists(os.path.join(project_root_path, dockerfile_path)):
        raise FileNotFoundError("Dockerfile not found in the project.")

    image = Build(
        build_spec=DockerFileBuild(
            dockerfile_path=dockerfile_path,
            command=command,
        ),
        build_source=LocalSource(project_root_path=project_root_path),
    )
    if component_type == ComponentType.SERVICE:
        if port is None:
            raise ValueError("Port is required for deploying service")
        app = Service(
            name=name,
            image=image,
            ports=[Port(port=port, expose=False)],
            env=env,
        )
    else:
        app = Job(name=name, image=image, env=env)
    app.deploy(workspace_fqn=workspace_fqn)


def _parse_env(project_root_path: str, env_path: str) -> Dict:
    if not os.path.isabs(env_path):
        env_path = os.path.join(project_root_path, env_path)

    if os.path.exists(env_path):
        return dotenv_values(env_path)

    raise FileNotFoundError(f"Invalid path {env_path!r}")


def _check_repo(project_root_path: str, console: Console):
    try:
        repo = Repo(project_root_path)
        if repo.is_dirty():
            console.print(
                "[bold red]Error:[/] The repository has uncommitted changes. Please commit or stash them before proceeding."
            )
            sys.exit(1)
        current_active_branch = repo.active_branch.name
        console.print(
            f"[bold magenta]TrueFoundry:[/] Current branch [green]{current_active_branch!r}[/]"
        )
        branch_name = Prompt.ask(
            "[bold magenta]TrueFoundry:[/] Enter a branch name if you want to checkout to a new branch. "
            f"Press enter to continue on [green]{current_active_branch!r}[/]",
            console=console,
        )
        if branch_name:
            repo.git.checkout("-b", branch_name)
            console.print(
                f"[bold magenta]TrueFoundry:[/] Switched to branch: [green]{repo.active_branch}[/]"
            )
        else:
            console.print(
                f"[bold magenta]TrueFoundry:[/] Continuing on [green]{current_active_branch!r}[/]"
            )

    except InvalidGitRepositoryError:
        console.print(
            "[red]Error:[/] This operation can only be performed inside a Git repository.\n"
            "Execute 'git init' to create a new repository."
        )
        sys.exit(1)

    except GitCommandError as gce:
        console.print(
            f"Command execution failed due to the following error:[red]{gce.stderr}[/]".replace(
                "\n  stderr:", ""
            )
        )
        console.print(
            "[bold red]Error:[/] Unable to switch to the new branch. It's possible that this branch already exists."
        )
        sys.exit(1)


def _update_status(event, status: Status):
    if isinstance(event, (AskQuestion, CommitConfirmation)):
        status.stop()

    if isinstance(
        event, (Developer.Request, ProjectIdentifier.Response, Tester.Response)
    ):
        status.update(
            "[bold magenta]TrueFoundry[/] is currently building the project. Please wait..."
        )

    if isinstance(event, ProjectIdentifier.Request):
        status.update(
            "[bold magenta]TrueFoundry[/] is currently identifying the project..."
        )

    if isinstance(event, (Tester.Request, DockerRun.Response)):
        status.update(
            "[bold magenta]TrueFoundry[/] is currently running tests on the project..."
        )

    if isinstance(event, DockerRunLog):
        status.update(
            "[bold cyan]Running:[/] [bold magenta]TrueFoundry[/] is executing the Docker container. Press [yellow]control-c[/] to stop waiting for additional logs..."
        )


def _get_default_project_name(project_root_path: str):
    path = os.path.abspath(project_root_path).rstrip(os.path.sep)
    name = path.split(os.path.sep)[-1].lower()
    name = re.sub(r"[^a-z0-9]", "-", name)
    name = "-".join(n for n in name.split("-") if n)[:30]
    return name


def _get_docker(console: Console) -> docker.DockerClient:
    try:
        return docker.from_env()
    except Exception:
        console.print_exception(extra_lines=0, max_frames=1)
        console.print(
            "[bold red]Error:[/] Could not connect to Docker, please check whether the Docker daemon is running."
        )
        sys.exit(1)


def cli(project_root_path: str, deploy: bool, workspace_fqn: str = None):
    console = Console()
    openai_client = _get_openai_client()
    docker_client = _get_docker(console)
    project_root_path = os.path.abspath(project_root_path)
    console.print(ABOUT_AUTODEPLOY)
    console.print(AUTODEPLOY_INTRO_MESSAGE)
    console.print(
        "[bold reverse]You will need to have Docker and Git installed on your machine for this to work[/]"
    )
    if AUTODEPLOY_OPENAI_BASE_URL is not None and AUTODEPLOY_OPENAI_API_KEY is not None:
        console.print(
            "[bold green]OpenAI credentials found in environment variables.[/]"
        )
        console.print(
            "This operation will use tokens from your provided OpenAI account and may incur costs.",
        )
    else:
        console.print(
            "[dim]To use your own LLM, set the environment variables [dim italic green]AUTODEPLOY_OPENAI_BASE_URL[/],[/]",
            "[dim][dim italic green]AUTODEPLOY_OPENAI_API_KEY[/], and [dim italic green]AUTODEPLOY_MODEL_NAME[/] for URL, API key, and LLM model name respectively.[/]",
        )
    console.print(
        "[bold cyan]Note:[/] All changes will be committed to a new branch. Please ensure you have a repository."
    )
    console.print("[bright_green]Let's get started[/]")
    _check_repo(project_root_path=project_root_path, console=console)

    choices = {
        "Service: An application that runs continuously. Example: web servers, workers polling a job queue, etc.": "SERVICE",
        "Job: An application that runs once and then stops. Example: Training an ML model, running a script, etc.": "JOB",
    }
    component = inquirer.prompt(
        [
            inquirer.List(
                "component",
                message="TrueFoundry: Is your project a",
                choices=choices.keys(),
            )
        ]
    )["component"]
    component_type = ComponentType[choices[component]]
    while True:
        name = Prompt.ask(
            "[bold magenta]TrueFoundry:[/] Name of deployment",
            console=console,
            default=_get_default_project_name(project_root_path),
        )
        if not re.match(r"^[a-z][a-z0-9\-]{1,30}[a-z0-9]$", name):
            console.print(
                "[bold magenta]TrueFoundry:[/] The name should be between 2-30 alphaneumaric"
                " characters and '-'. The first character should not be a digit."
            )
        else:
            break
    command = Prompt.ask(
        "[bold magenta]TrueFoundry:[/] Command to run the application",
        console=console,
        show_default=False,
        default=None,
    )

    env_path = Prompt.ask(
        "[bold magenta]TrueFoundry:[/] Enter .env file location for environment variables, "
        "or press [green]Enter[/] to skip.",
        console=console,
    )
    if workspace_fqn is None:
        workspace_fqn = Prompt.ask(
            "[bold magenta]TrueFoundry:[/] Enter the Workspace FQN where you would like to deploy, [dim]Ex: cluster-name:workspace-name[/]"
        )
    while True:
        try:
            env = _parse_env(project_root_path, env_path) if env_path else {}
            break
        except FileNotFoundError:
            console.print("[red]Invalid location for .env[/]")
            env_path = Prompt.ask(
                "[bold magenta]TrueFoundry:[/]Please provide the correct path,"
                "or press [green]Enter[/] to skip.",
                console=console,
            )
            continue
    status = console.status(
        "[bold cyan]Starting up:[/] [bold magenta]TrueFoundry[/] is initializing. Please wait..."
    )
    with status:
        developer = Developer(
            project_root_path=project_root_path,
            openai_client=openai_client,
            docker_client=docker_client,
            environment=env,
        )
        developer_run = developer.run(developer.Request(command=command, name=name))
        inp = None
        response = None
        while True:
            try:
                status.start()
                event = developer_run.send(inp)
                _update_status(event=event, status=status)
                inp = event.render(console)
            except StopIteration as ex:
                response = ex.value
                break

    if deploy:
        deploy_component(
            workspace_fqn=workspace_fqn,
            project_root_path=project_root_path,
            dockerfile_path=response.dockerfile_path,
            name=name,
            component_type=component_type,
            env=env,
            command=response.command,
            port=response.port,
        )


@click.command(name="auto-deploy", cls=COMMAND_CLS)
@click.option(
    "--path", type=click.STRING, required=True, help="The root path of the project"
)
@click.option(
    "--deploy",
    type=click.BOOL,
    is_flag=True,
    default=True,
    show_default=True,
    help="Deploy the project after successfully building it.",
)
def autodeploy_cli(path: str, deploy: bool):
    """
    Build and deploy projects using Truefoundry
    """
    cli(
        project_root_path=path,
        deploy=deploy,
    )
