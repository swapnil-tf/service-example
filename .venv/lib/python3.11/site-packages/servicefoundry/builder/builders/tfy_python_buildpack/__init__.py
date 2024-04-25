import os
from tempfile import TemporaryDirectory
from typing import List, Optional

from servicefoundry.auto_gen.models import DockerFileBuild, PythonBuild
from servicefoundry.builder.builders import dockerfile
from servicefoundry.builder.builders.tfy_python_buildpack.dockerfile_template import (
    generate_dockerfile_content,
)

__all__ = ["generate_dockerfile_content", "build"]


def _convert_to_dockerfile_build_config(
    build_configuration: PythonBuild,
    dockerfile_path: str,
) -> DockerFileBuild:
    dockerfile_content = generate_dockerfile_content(
        build_configuration=build_configuration
    )
    with open(dockerfile_path, "w", encoding="utf8") as fp:
        fp.write(dockerfile_content)

    return DockerFileBuild(
        type="dockerfile",
        dockerfile_path=dockerfile_path,
        build_context_path=build_configuration.build_context_path,
    )


def build(
    tag: str,
    build_configuration: PythonBuild,
    extra_opts: Optional[List[str]] = None,
):
    with TemporaryDirectory() as local_dir:
        docker_build_configuration = _convert_to_dockerfile_build_config(
            build_configuration, dockerfile_path=os.path.join(local_dir, "Dockerfile")
        )
        dockerfile.build(
            tag=tag,
            build_configuration=docker_build_configuration,
            extra_opts=extra_opts,
        )
