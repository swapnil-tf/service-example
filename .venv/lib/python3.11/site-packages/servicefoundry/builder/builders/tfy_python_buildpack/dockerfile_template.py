import os
from typing import Dict, List, Optional

from mako.template import Template

from servicefoundry.auto_gen.models import PythonBuild
from servicefoundry.v2.lib.patched_models import CUDAVersion

# TODO (chiragjn): Switch to a non-root user inside the container

_POST_PYTHON_INSTALL_TEMPLATE = """
% if apt_install_command is not None:
RUN ${apt_install_command}
% endif

% if requirements_path is not None:
COPY ${requirements_path} ${requirements_destination_path}
% endif

% if pip_install_command is not None:
RUN ${pip_install_command}
% endif

COPY . /app
WORKDIR /app
"""

DOCKERFILE_TEMPLATE = Template(
    """
FROM --platform=linux/amd64 python:${python_version}
ENV PATH=/virtualenvs/venv/bin:$PATH
RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends git && \
    python -m venv /virtualenvs/venv/ && \
    rm -rf /var/lib/apt/lists/*
"""
    + _POST_PYTHON_INSTALL_TEMPLATE
)

CUDA_DOCKERFILE_TEMPLATE = Template(
    """
FROM --platform=linux/amd64 nvidia/cuda:${nvidia_cuda_image_tag}
ENV PATH=/virtualenvs/venv/bin:$PATH
RUN echo "deb https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu $(cat /etc/os-release | grep UBUNTU_CODENAME | cut -d = -f 2) main" >> /etc/apt/sources.list && \
    echo "deb-src https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu $(cat /etc/os-release | grep UBUNTU_CODENAME | cut -d = -f 2) main" >> /etc/apt/sources.list && \
    apt-key adv --keyserver keyserver.ubuntu.com --recv-keys F23C5A6CF475977595C89F51BA6932366A755776 && \
    apt update && \
    DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends git python${python_version}-dev python${python_version}-venv && \
    python${python_version} -m venv /virtualenvs/venv/ && \
    rm -rf /var/lib/apt/lists/*
"""
    + _POST_PYTHON_INSTALL_TEMPLATE
)

CUDA_VERSION_TO_IMAGE_TAG: Dict[str, str] = {
    CUDAVersion.CUDA_11_0_CUDNN8.value: "11.0.3-cudnn8-runtime-ubuntu20.04",
    CUDAVersion.CUDA_11_1_CUDNN8.value: "11.1.1-cudnn8-runtime-ubuntu20.04",
    CUDAVersion.CUDA_11_2_CUDNN8.value: "11.2.2-cudnn8-runtime-ubuntu20.04",
    CUDAVersion.CUDA_11_3_CUDNN8.value: "11.3.1-cudnn8-runtime-ubuntu20.04",
    CUDAVersion.CUDA_11_4_CUDNN8.value: "11.4.3-cudnn8-runtime-ubuntu20.04",
    CUDAVersion.CUDA_11_5_CUDNN8.value: "11.5.2-cudnn8-runtime-ubuntu20.04",
    CUDAVersion.CUDA_11_6_CUDNN8.value: "11.6.2-cudnn8-runtime-ubuntu20.04",
    CUDAVersion.CUDA_11_7_CUDNN8.value: "11.7.1-cudnn8-runtime-ubuntu22.04",
    CUDAVersion.CUDA_11_8_CUDNN8.value: "11.8.0-cudnn8-runtime-ubuntu22.04",
    CUDAVersion.CUDA_12_0_CUDNN8.value: "12.0.1-cudnn8-runtime-ubuntu22.04",
    CUDAVersion.CUDA_12_1_CUDNN8.value: "12.1.1-cudnn8-runtime-ubuntu22.04",
    CUDAVersion.CUDA_12_2_CUDNN8.value: "12.2.2-cudnn8-runtime-ubuntu22.04",
}


def resolve_requirements_txt_path(build_configuration: PythonBuild) -> Optional[str]:
    if build_configuration.requirements_path:
        return build_configuration.requirements_path

    # TODO: what if there is a requirements.txt but user does not wants us to use it.
    possible_requirements_txt_path = os.path.join(
        build_configuration.build_context_path, "requirements.txt"
    )

    if os.path.isfile(possible_requirements_txt_path):
        return os.path.relpath(
            possible_requirements_txt_path, start=build_configuration.build_context_path
        )

    return None


def generate_apt_install_command(apt_packages: Optional[List[str]]) -> Optional[str]:
    packages_list = None
    if apt_packages:
        packages_list = " ".join(p.strip() for p in apt_packages if p.strip())
    if not packages_list:
        return None
    apt_update_command = "apt update"
    apt_install_command = f"DEBIAN_FRONTEND=noninteractive apt install -y --no-install-recommends {packages_list}"
    clear_apt_lists_command = "rm -rf /var/lib/apt/lists/*"
    return " && ".join(
        [apt_update_command, apt_install_command, clear_apt_lists_command]
    )


def generate_pip_install_command(
    requirements_path: Optional[str], pip_packages: Optional[List[str]]
) -> Optional[str]:
    upgrade_pip_command = "python -m pip install -U pip setuptools wheel"
    final_pip_install_command = None
    pip_install_base_command = "python -m pip install --use-pep517 --no-cache-dir"
    if requirements_path:
        final_pip_install_command = f"{pip_install_base_command} -r {requirements_path}"

    if pip_packages:
        final_pip_install_command = (
            final_pip_install_command or pip_install_base_command
        )
        final_pip_install_command += " " + " ".join(
            f"'{package}'" for package in pip_packages
        )

    if not final_pip_install_command:
        return None

    return " && ".join([upgrade_pip_command, final_pip_install_command])


def generate_dockerfile_content(
    build_configuration: PythonBuild,
) -> str:
    # TODO (chiragjn): Handle recursive references to other requirements files e.g. `-r requirements-gpu.txt`
    requirements_path = resolve_requirements_txt_path(build_configuration)
    requirements_destination_path = (
        "/tmp/requirements.txt" if requirements_path else None
    )
    pip_install_command = generate_pip_install_command(
        requirements_path=requirements_destination_path,
        pip_packages=build_configuration.pip_packages,
    )
    apt_install_command = generate_apt_install_command(
        apt_packages=build_configuration.apt_packages
    )

    template_args = dict(
        python_version=build_configuration.python_version,
        apt_install_command=apt_install_command,
        requirements_path=requirements_path,
        requirements_destination_path=requirements_destination_path,
        pip_install_command=pip_install_command,
    )

    if build_configuration.cuda_version:
        template = CUDA_DOCKERFILE_TEMPLATE
        template_args["nvidia_cuda_image_tag"] = CUDA_VERSION_TO_IMAGE_TAG.get(
            build_configuration.cuda_version, build_configuration.cuda_version
        )
    else:
        template = DOCKERFILE_TEMPLATE

    dockerfile_content = template.render(**template_args)
    return dockerfile_content
