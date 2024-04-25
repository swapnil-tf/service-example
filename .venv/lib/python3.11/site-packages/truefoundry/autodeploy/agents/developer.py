from __future__ import annotations

from typing import Dict, Optional

import docker
from openai import OpenAI
from pydantic import Field

from truefoundry.autodeploy.agents.base import Agent
from truefoundry.autodeploy.agents.project_identifier import ProjectIdentifier
from truefoundry.autodeploy.agents.tester import Tester
from truefoundry.autodeploy.tools import (
    Ask,
    Commit,
    DockerBuild,
    ListFiles,
    ReadFile,
    RequestEvent,
    ResponseEvent,
)


class Developer(Agent):
    system_prompt = """
You are a software engineer.
You goal is to do whatever you have to do to succesfully run a project.
If the project already contains a dockerfile, you can use that.
If the project does not contain a dockerfile, you have to create one.
You need to fix any issue to ensure that the image builds succesfully.
Generate syntactically correct Dockerfile.
You need to always read a file before making any changes.
Ensure that you always make changes if you are writing a file.
This is the rough flow you have to follow:
Identify Project -> Build Docker Image -> Tester
If Tester is not successful, you need to fix the issue and try Tester again.
Tester has the final authority over whether you were successful in your task.
Do not ask the user to manually review anything. You need to review and and take a decision.
You can ask questions to the user but you need to take actions to run the project.
Do not ask users how to fix an issue.
Communicate with the user only via Ask tool.
You should add Dockerfile path to .dockerignore file, this will speed up iteration.
You can create a .dockerignore file if it does not exist.
Try to download dependencies first, before you copy the whole project. This will speed up
subsequent builds due to build cache.
Use the Project identifier tool call to identify project.
Avoid reading *.lock type files as they tend to be large
If you are using multi-stage build:
1. For a go project  the final stage should not need a go runtime.
2. If you get a missing file error because the application is trying to load a file, you should
   add the files in the final stage.
3. While copying the file, be careful about the destination directory.

For Golang projects:
1. you need to ensure you know where is the main.go file. Sometimes it can be in cmd dir.

    """
    max_iter = 50

    class Request(RequestEvent):
        name: str = Field(..., description="Name of the project.")
        command: Optional[str] = Field(
            None,
            description="Preferred command to run project. This can be corrected later.",
        )

    class Response(ResponseEvent):
        command: str = Field(
            description="""
Final command to run the project within the container.
This command should be same as what is expressed uning
the entrypoint and cmd of the dockerfile.
        """
        )
        dockerfile_path: str = Field(description="Path of dockerfile.")
        port: Optional[int] = Field(description="Port in which container is running.")
        justification: str = Field(
            ...,
            description="""
            Why did you send the response back?
        """,
        )

    def __init__(
        self,
        project_root_path: str,
        docker_client: docker.DockerClient,
        openai_client: OpenAI,
        environment: Dict,
    ):
        self.tools = [
            DockerBuild(
                project_root_path=project_root_path,
                docker_client=docker_client,
            ),
            ReadFile(
                project_root_path=project_root_path,
            ),
            Commit(project_root_path=project_root_path),
            ListFiles(
                project_root_path=project_root_path,
            ),
            ProjectIdentifier(
                project_root_path=project_root_path,
                openai_client=openai_client,
            ),
            Tester(
                openai_client=openai_client,
                docker_client=docker_client,
                environment=environment,
            ),
            Ask(),
        ]
        self.openai_client = openai_client
