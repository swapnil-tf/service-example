from typing import List, Optional

from mako.template import Template

from servicefoundry.pydantic_v1 import BaseModel


class NotebookImageBuild(BaseModel):
    type: str
    base_image_uri: str
    apt_packages: List[str]


DOCKERFILE_TEMPLATE = Template(
    """
FROM ${base_image_uri}
USER root
RUN ${apt_install_command}
USER $NB_UID
"""
)


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


def generate_dockerfile_content(build_configuration: NotebookImageBuild) -> str:
    apt_install_command = generate_apt_install_command(
        apt_packages=build_configuration.apt_packages
    )

    template_args = dict(
        base_image_uri=build_configuration.base_image_uri,
        apt_install_command=apt_install_command,
    )

    template = DOCKERFILE_TEMPLATE

    dockerfile_content = template.render(**template_args)
    return dockerfile_content
