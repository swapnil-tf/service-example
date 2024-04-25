from __future__ import annotations

import os
from collections import Counter
from typing import Any, Dict, Generator

import gitignorefile
from pydantic import Field
from rich.console import Console
from rich.table import Table

from truefoundry.autodeploy.tools.base import (
    Event,
    Message,
    RequestEvent,
    ResponseEvent,
    Tool,
)


class ShowFileCount(Event):
    file_types: Dict[str, int]

    def render(self, console: Console):
        total_files = sum(self.file_types.values())
        console.print(f"Found {total_files} files.")
        table = Table()
        table.add_column("File Type", style="cyan")
        table.add_column("Count", justify="right", style="green")
        for file_type, count in self.file_types.items():
            table.add_row(file_type, str(count))

        console.print(table)


class FileTypeCounts(Tool):
    description = """
Get counts of different types of file present.
"""

    class Request(RequestEvent): ...

    class Response(ResponseEvent):
        file_types: Dict[str, int] = Field(
            ...,
            description='Counts of different types of files. Ex: {"py": 1} or {"c": 1}',
        )

    def __init__(self, project_root_path: str):
        self.project_root_path = project_root_path

    def run(
        self, request: FileTypeCounts.Request
    ) -> Generator[Event, Any, ResponseEvent]:
        counter = Counter()

        yield Message(
            message="[bold cyan]Processing:[/] Scanning for various file types..."
        )

        def gitignore(_):
            return False

        gitignore_path = os.path.join(self.project_root_path, ".gitignore")
        if os.path.exists(gitignore_path):
            gitignore = gitignorefile.parse(path=gitignore_path)
        for root, dirs, ps in os.walk(
            self.project_root_path,
        ):
            root = root[len(self.project_root_path) :]
            if ".git" in dirs:
                dirs.remove(".git")
            counter.update(
                p.split(".")[-1] if len(p) and p[0] != "." else p
                for p in ps
                if not gitignore(os.path.join(root, p).strip(os.path.sep))
            )
        yield ShowFileCount(file_types=counter)
        return FileTypeCounts.Response(file_types=counter)
