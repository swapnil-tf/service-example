import json
import sys
from typing import List, Optional

from servicefoundry.function_service.route import RouteGroups
from servicefoundry.logger import logger
from servicefoundry.pydantic_v1 import BaseModel, constr
from servicefoundry.v2.lib.patched_models import PythonBuild
from servicefoundry.version import __version__


class BuildConfig(BaseModel):
    python_version: constr(
        regex=r"^\d+(\.\d+){1,2}$"
    ) = f"{sys.version_info.major}.{sys.version_info.minor}"
    pip_packages: Optional[List[str]]
    requirements_path: Optional[str] = None

    def __init__(self, **data):
        pip_packages = data.get("pip_packages", [])
        # locally version == 0.0.0
        # pip_packages.append(f"servicefoundry=={__version__}")

        if __version__ in ("NA", "0.0.0"):
            # TODO (chiragjn): Any change to servicefoundry.function_service.__main__ is untestable!
            #   We need to vendor `servicefoundry.function_service` parts in the local source to be able to test.
            sfy_version = ">=0.7.0,<0.9.0"
            logger.info(
                "Could not detect servicefoundry version. Using %r", sfy_version
            )
        else:
            sfy_version = f"=={__version__}"

        pip_packages.append(f"servicefoundry{sfy_version}")
        data["pip_packages"] = pip_packages
        super().__init__(**data)

    def to_tfy_python_build_config(
        self, port: int, route_groups: RouteGroups
    ) -> PythonBuild:
        escaped_route_groups_json = json.dumps(route_groups.json())
        return PythonBuild(
            python_version=self.python_version,
            pip_packages=self.pip_packages,
            requirements_path=self.requirements_path,
            command=f"python -m servicefoundry.function_service run --port {port} --route-groups-json {escaped_route_groups_json}",
        )
