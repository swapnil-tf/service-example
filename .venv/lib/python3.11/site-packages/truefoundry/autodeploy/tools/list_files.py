from __future__ import annotations

import os
from fnmatch import fnmatch
from typing import Any, Generator, List, Optional

import gitignorefile
from pydantic import Field

from truefoundry.autodeploy.tools.base import (
    Event,
    Message,
    RequestEvent,
    ResponseEvent,
    Tool,
)


class ListFiles(Tool):
    description = """
List all files.
If you want to find all json files recuresively under directory a/b
the subdir should be a/b and pattern will be *.json

If you want to find all json files recuresively under current directory
the subdir should be . and pattern will be *.json
"""

    class Request(RequestEvent):
        sub_dir: str
        pattern: str = Field(..., description="Glob pattern. Avoid passing '*'")

    class Response(ResponseEvent):
        paths: List[str] = Field(
            ...,
            description="File paths under the given directory",
        )
        error: Optional[str] = Field(None)

    def __init__(self, project_root_path: str):
        self.project_root_path = project_root_path

    def run(self, request: ListFiles.Request) -> Generator[Event, Any, ResponseEvent]:
        yield Message(
            message=f"[bold cyan]Searching:[/] 🔍 Looking for files matching the pattern [magenta]{request.pattern}[/]"
        )

        paths: List[str] = []

        def gitignore(_):
            return False

        gitignore_path = os.path.join(self.project_root_path, ".gitignore")
        if os.path.exists(gitignore_path):
            gitignore = gitignorefile.parse(path=gitignore_path)

        path = os.path.join(self.project_root_path, request.sub_dir.strip(os.path.sep))
        if not os.path.exists(path):
            return ListFiles.Response(
                paths=None,
                error=f"Incorrect sub_dir {request.sub_dir}. Does not exist",
            )

        for root, dirs, ps in os.walk(
            path,
        ):
            root = root[len(path) :]
            if ".git" in dirs:
                dirs.remove(".git")
            paths.extend(
                os.path.join(root, p).lstrip(os.path.sep)
                for p in ps
                if fnmatch(p, request.pattern)
                and not gitignore(os.path.join(root, p).strip(os.path.sep))
            )
        if len(paths) > 0:
            yield Message(message=f"[bold green]Success:[/] Found {len(paths)} files.")
        else:
            yield Message(
                message=f"[red]Alert:[/] No files found matching the pattern {request.pattern}."
            )
        return ListFiles.Response(paths=paths)
