from __future__ import annotations

import enum
from typing import List, Optional

from openai import OpenAI
from pydantic import Field
from rich.console import Console

from truefoundry.autodeploy.agents.base import Agent
from truefoundry.autodeploy.tools import (
    Ask,
    FileTypeCounts,
    ListFiles,
    ReadFile,
    RequestEvent,
    ResponseEvent,
)


class ComponentType(str, enum.Enum):
    SERVICE = "SERVICE"
    JOB = "JOB"


class ProjectIdentifier(Agent):
    description = """
Identify the type of project.
"""
    system_prompt = """
Your goal is to figure out the type of project.
Once you figure out, send the Response tool call.
The information will be later used to build a Dockerfile.
Try to figure out ALL the response tool field arguments even if something is optional.
Prefer reading files like requirements.txt, pyproject.toml, go.mod, packages.json to figure out framework.
You should have strong justification for your response. Do not assume anything.
Prefer using file type counts over list files.
use the knowledge of file type counts to create the right glob pattern while listing files.
Prefer yarn over npm if the project is using yarn.
If there is  a lock file, the project maybe using yarn.
Look for *.lock if there is a lock type file persent.
Always response with a function call.
    """
    max_iter = 10

    class Request(RequestEvent): ...

    class Response(ResponseEvent):
        component_type: Optional[ComponentType] = Field(
            None,
            description="""
A Service is designed to run always and should never terminate.
A Job is desiged to finish after sometime.
""",
        )
        primary_programming_language: str = Field(
            ...,
            description="""
Primary programming language used for the project.
Ex: Go, Python, Rust, Typescript, etc.",
""",
        )
        framework: Optional[str] = Field(
            None,
            description="""
If the project is using any specific framework.
Ex: FastAPI, Gin, Flask, NestJS, React, etc.
            """,
        )
        version: Optional[str] = Field(
            None,
            description="""
Identifies and return the exact version of the project's programming language,
essential for successful Docker image creation and execution.""",
        )
        dependency_files: Optional[List[str]] = Field(
            None,
            descripton="""
requirements.txt, poetry.lock, yarn.lock, Cargo.lock, go.mod, go.sum, pyproject.toml, etc.
There can be multiple files like ["pyproject.toml", "poetry.lock"] or ["yarn.lock", "package.json"]
                                                  """,
        )
        dependency_manager: Optional[str] = Field(
            None,
            descripton="""
pip, poetry, yarn, go.mod, cargo.toml, npm, setup.py.
                                                  """,
        )
        justification: str = Field(
            ...,
            description="Justification behind each response field.",
        )

        def render(self, console: Console):
            if self.primary_programming_language is not None:
                console.print(
                    f"[bold magenta]TrueFoundry:[/] Identified a project using [bold cyan]{self.primary_programming_language}[/]."
                )
                console.print(
                    f"[bold magenta]TrueFoundry:[/] Framework Identified: [bold cyan]{'Not applicable' if self.framework is None else self.framework}[/]"
                )
                console.print(
                    f"[bold magenta]TrueFoundry:[/] Dependency Manager Identified: [bold cyan]{'Not applicable' if self.dependency_manager is None else self.dependency_manager}[/]"
                )
            else:
                console.print(
                    "[bold magenta]TrueFoundry:[/] Unable to identify any programming language in the project."
                )
            console.print(
                f"[bold magenta]TrueFoundry:[/] [italic]{self.justification}[/]"
            )

    def __init__(self, project_root_path: str, openai_client: OpenAI):
        self.tools = [
            ReadFile(
                project_root_path=project_root_path,
            ),
            ListFiles(
                project_root_path=project_root_path,
            ),
            FileTypeCounts(project_root_path=project_root_path),
            Ask(),
        ]
        self.openai_client = openai_client
