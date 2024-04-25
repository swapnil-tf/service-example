import os
import tarfile
import tempfile
import time
import warnings
from typing import Callable, List, Optional

import gitignorefile
from tqdm import tqdm

from servicefoundry import builder
from servicefoundry.auto_gen import models
from servicefoundry.builder.docker_service import (
    pull_docker_image,
    push_docker_image,
    push_docker_image_with_latest_tag,
)
from servicefoundry.lib.clients.service_foundry_client import (
    ServiceFoundryServiceClient,
)
from servicefoundry.lib.dao import workspace as workspace_lib
from servicefoundry.logger import logger
from servicefoundry.v2.lib.patched_models import Image, RemoteSource


def _human_readable_size(num_bytes: float) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    i = 0
    amount = num_bytes
    while amount >= 1024 and i < len(units) - 1:
        amount /= 1024.0
        i += 1
    amount = round(amount, 2)
    return f"{amount} {units[i]}"


def _make_tarfile(
    output_filename: str,
    source_dir: str,
    additional_directories: List[str],
    is_path_ignored: Optional[Callable[[str], bool]] = None,
) -> None:
    if not is_path_ignored:
        # if no callback handler present assume that every file needs to be added
        is_path_ignored = lambda *_: False

    with tarfile.open(output_filename, "w:gz") as tar:
        source_dirs = [source_dir]
        source_dirs.extend(additional_directories)
        for source_dir in source_dirs:
            _add_files_in_tar(
                is_path_ignored=is_path_ignored,
                source_dir=source_dir,
                tar=tar,
            )


def _add_files_in_tar(
    is_path_ignored: Callable[[str], bool],
    source_dir: str,
    tar: tarfile.TarFile,
) -> None:
    for root, dirs, files in tqdm(
        os.walk(source_dir, topdown=True), desc="Packaging source code"
    ):
        if is_path_ignored(root):
            logger.debug("Ignoring directory %s", root)

            # NOTE: we can safely ignore going through the sub-dir
            # if root itself is excluded.
            dirs.clear()
            continue
        logger.debug("Adding contents of the directory %s", root)
        files_added_count = 0
        for file in files:
            file_path = os.path.join(root, file)
            if not is_path_ignored(file_path):
                arcname = os.path.relpath(file_path, source_dir)
                tar.add(file_path, arcname=arcname)
                logger.debug("Adding %s with arcname %r", file_path, arcname)
                files_added_count += 1

        if not files_added_count:
            # If no files were added and the directory was not ignored too, then we
            # want to add the directory as an empty dir
            arcname = os.path.relpath(root, source_dir)
            tar.add(root, arcname=arcname, recursive=False)
            logger.debug("Adding empty directory %s with arcname %r", root, arcname)


def _get_callback_handler_to_ignore_file_path(
    source_dir: str,
) -> Optional[Callable[[str], bool]]:
    ignorefile_path = os.path.join(source_dir, ".tfyignore")
    if os.path.exists(ignorefile_path):
        logger.info(".tfyignore file found in %s", source_dir)
        return gitignorefile.parse(path=ignorefile_path, base_path=source_dir)

    ignorefile_path = os.path.join(source_dir, ".sfyignore")
    if os.path.exists(ignorefile_path):
        logger.info(".sfyignore file found in %s", source_dir)
        warnings.warn(
            "`.sfyignore` is deprecated and will be ignored in future versions. "
            "Please rename the file to `.tfyignore`",
            category=DeprecationWarning,
        )
        return gitignorefile.parse(path=ignorefile_path, base_path=source_dir)

    # check for valid git repo
    try:
        import git

        repo = git.Repo(source_dir, search_parent_directories=True)
        logger.info(
            "Git repository detected in source. Files added in .gitignore will be ignored.\n"
            "If you don't want to ignore these files or otherwise, "
            "please create .tfyignore file and add file patterns to ignore."
        )
        return lambda file_path: bool(repo.ignored(file_path))
    except Exception as ex:
        logger.debug(
            "Could not treat source %r as a git repository due to %r", source_dir, ex
        )

    logger.info(
        "Neither `.tfyignore` file found in %s nor a valid git repository found. "
        "We recommend you to create .tfyignore file and add file patterns to ignore",
        source_dir,
    )
    return None


def local_source_to_remote_source(
    local_source: models.LocalSource,
    workspace_fqn: str,
    component_name: str,
) -> RemoteSource:
    with tempfile.TemporaryDirectory() as local_dir:
        package_local_path = os.path.join(local_dir, "build.tar.gz")
        source_dir = os.path.abspath(local_source.project_root_path)

        if not os.path.exists(source_dir):
            raise ValueError(
                f"project root path {source_dir!r} of component {component_name!r} does not exist"
            )

        logger.info("Archiving contents of dir: %r", source_dir)

        is_path_ignored = _get_callback_handler_to_ignore_file_path(source_dir)
        _make_tarfile(
            output_filename=package_local_path,
            source_dir=source_dir,
            additional_directories=[],
            is_path_ignored=is_path_ignored,
        )

        try:
            file_size = _human_readable_size(os.path.getsize(package_local_path))
            logger.info("Code archive size: %r", file_size)
        except Exception:
            # Should not block code upload
            logger.exception("Failed to calculate code archive size")

        logger.debug("Uploading code archive.")
        client = ServiceFoundryServiceClient()
        remote_uri = client.upload_code_package(
            workspace_fqn=workspace_fqn,
            component_name=component_name,
            package_local_path=package_local_path,
        )
        logger.debug("Uploaded code archive.")
        return RemoteSource(remote_uri=remote_uri)


def local_source_to_image(
    build: models.Build,
    docker_registry_fqn: Optional[str],
    workspace_fqn: str,
    component_name: str,
) -> Image:
    build = build.copy(deep=True)
    source_dir = os.path.abspath(
        os.path.expanduser(build.build_source.project_root_path)
    )
    if not os.path.exists(source_dir):
        raise ValueError(
            f"project root path {source_dir!r} of component {component_name!r} does not exist"
        )

    build.build_spec.build_context_path = os.path.join(
        source_dir, build.build_spec.build_context_path
    )
    if not os.path.exists(build.build_spec.build_context_path):
        raise ValueError(
            f"Build context path {build.build_spec.build_context_path!r} "
            f"of component {component_name!r} does not exist"
        )

    if isinstance(build.build_spec, models.DockerFileBuild):
        build.build_spec.dockerfile_path = os.path.join(
            source_dir, build.build_spec.dockerfile_path
        )
        if not os.path.exists(build.build_spec.dockerfile_path):
            raise ValueError(
                f"Dockerfile path {build.build_spec.dockerfile_path!r} "
                f"of component {component_name!r} does not exist"
            )

    client = ServiceFoundryServiceClient()

    workspace = workspace_lib.get_workspace_by_fqn(workspace_fqn=workspace_fqn)
    docker_registry = client.get_docker_registry_creds(
        docker_registry_fqn=docker_registry_fqn,
        cluster_id=workspace.clusterId,
    )

    docker_registry_fqn = docker_registry.fqn
    registry_url = docker_registry.registryUrl
    registry_username = docker_registry.username
    registry_password = docker_registry.password

    create_repo_response = client.create_repo_in_registry(
        docker_registry_fqn=docker_registry_fqn,
        workspace_fqn=workspace_fqn,
        application_name=component_name,
    )
    repo_name = create_repo_response.repoName

    image_uri = f"{registry_url}/{repo_name}:{int(time.time())}"
    cache_from = f"{registry_url}/{repo_name}:latest"

    # pull cache image if it exists
    try:
        pull_docker_image(
            image_uri=cache_from,
            docker_login_username=registry_username,
            docker_login_password=registry_password,
        )
    except Exception:
        logger.info(f"Failed to pull {cache_from}. Building without cache image.")

    # build
    builder.build(
        build.build_spec,
        tag=image_uri,
        extra_opts=["--cache-from", cache_from],
    )

    # push built image to registry
    push_docker_image(
        image_uri=image_uri,
        docker_login_username=registry_username,
        docker_login_password=registry_password,
    )

    # push 'latest' tag for image
    push_docker_image_with_latest_tag(
        image_uri=image_uri,
        docker_login_username=registry_username,
        docker_login_password=registry_password,
    )
    return Image(
        image_uri=image_uri,
        docker_registry=docker_registry_fqn,
        command=build.build_spec.command,
    )
