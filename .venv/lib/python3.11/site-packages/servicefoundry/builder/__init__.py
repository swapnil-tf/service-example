from typing import Dict, List, Optional, Union

from servicefoundry.auto_gen.models import DockerFileBuild, PythonBuild
from servicefoundry.builder.builders import get_builder
from servicefoundry.builder.builders.tfy_notebook_buildpack.dockerfile_template import (
    NotebookImageBuild,
)
from servicefoundry.pydantic_v1 import BaseModel


class _BuildConfig(BaseModel):
    # I cannot use Field(discriminator="build_config_type") here as
    # build_config_type in the build configs is not a Literal.
    __root__: Union[DockerFileBuild, PythonBuild, NotebookImageBuild]


def build(
    build_configuration: Union[BaseModel, Dict],
    tag: str,
    extra_opts: Optional[List[str]] = None,
):
    build_configuration = _BuildConfig.parse_obj(build_configuration).__root__
    builder = get_builder(build_configuration.type)
    return builder(
        build_configuration=build_configuration,
        tag=tag,
        extra_opts=extra_opts,
    )


if __name__ == "__main__":
    # TODO: remove these and write tests for Build class to dockerfile content.
    import os
    from tempfile import TemporaryDirectory

    with TemporaryDirectory() as local_dir:
        dockerfile_path = os.path.join(local_dir, "Dockerfile.test")
        with open(dockerfile_path, "w", encoding="utf8") as fp:
            fp.write("from postgres:latest")

        build_config = DockerFileBuild(
            type="dockerfile",
            build_context_path=local_dir,
            dockerfile_path=dockerfile_path,
        )

        build(tag="docker-test", build_configuration=build_config)

    with TemporaryDirectory() as local_dir:
        requirements_path = os.path.join(local_dir, "requirements.txt")
        with open(requirements_path, "w", encoding="utf8") as fp:
            fp.write("requests")

        python_path = os.path.join(local_dir, "main.py")
        with open(python_path, "w", encoding="utf8") as fp:
            fp.write("import requests; print(requests.__version__);")

        build_config = PythonBuild(
            type="tfy-python-buildpack",
            build_context_path=local_dir,
            command=["python", "main.py"],
            python_version="3.7.13",
        )
        build(tag="python-test-exec", build_configuration=build_config)
        build_config = PythonBuild(
            type="tfy-python-buildpack",
            build_context_path=local_dir,
            command="python main.py",
            python_version="3.8",
        )
        build(tag="python-test-shell", build_configuration=build_config)

    with TemporaryDirectory() as local_dir:
        requirements_path = os.path.join(local_dir, "requirements.txt")
        with open(requirements_path, "w", encoding="utf8") as fp:
            fp.write("numpy")

        python_path = os.path.join(local_dir, "main.py")
        with open(python_path, "w", encoding="utf8") as fp:
            fp.write("import numpy; import requests; print(requests.__version__);")

        build_config = PythonBuild(
            type="tfy-python-buildpack",
            build_context_path=local_dir,
            command=["python", "main.py"],
            python_version="3.7.13",
            pip_packages=["requests"],
        )
        build(tag="python-pip-and-req-file", build_configuration=build_config)

    with TemporaryDirectory() as local_dir:
        python_path = os.path.join(local_dir, "main.py")
        with open(python_path, "w", encoding="utf8") as fp:
            fp.write("import requests; print(requests.__version__);")

        build_config = PythonBuild(
            type="tfy-python-buildpack",
            build_context_path=local_dir,
            command=["python", "main.py"],
            python_version="3.7.13",
            pip_packages=["requests>0.1"],
        )
        build(tag="python-only-pip", build_configuration=build_config)

    with TemporaryDirectory() as local_dir:
        python_path = os.path.join(local_dir, "main.py")
        with open(python_path, "w", encoding="utf8") as fp:
            fp.write("print(1)")

        build_config = PythonBuild(
            type="tfy-python-buildpack",
            build_context_path=local_dir,
            command=["python", "main.py"],
            python_version="3.7.13",
        )
        build(tag="python-only-no-pip-no-req", build_configuration=build_config)
