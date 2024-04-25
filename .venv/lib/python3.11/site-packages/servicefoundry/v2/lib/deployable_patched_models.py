from typing import Union

from servicefoundry.auto_gen import models
from servicefoundry.lib.model.entity import Deployment
from servicefoundry.pydantic_v1 import BaseModel, Field, conint, constr
from servicefoundry.v2.lib.deploy import deploy_component


class DeployablePatchedModelBase(BaseModel):
    class Config:
        extra = "forbid"

    def deploy(self, workspace_fqn: str, wait: bool = True) -> Deployment:
        return deploy_component(component=self, workspace_fqn=workspace_fqn, wait=wait)


class Service(models.Service, DeployablePatchedModelBase):
    type: constr(regex=r"service") = "service"
    resources: models.Resources = Field(default_factory=models.Resources)
    # This is being patched because cue export marks this as a "number"
    replicas: Union[conint(ge=0, le=100), models.ServiceAutoscaling] = Field(
        1,
        description="+label=Replicas\n+usage=Replicas of service you want to run\n+icon=fa-clone\n+sort=3",
    )


class Job(models.Job, DeployablePatchedModelBase):
    type: constr(regex=r"job") = "job"
    resources: models.Resources = Field(default_factory=models.Resources)


class Notebook(models.Notebook, DeployablePatchedModelBase):
    type: constr(regex=r"^notebook$") = "notebook"
    resources: models.Resources = Field(default_factory=models.Resources)


class Codeserver(models.Codeserver, DeployablePatchedModelBase):
    type: constr(regex=r"^codeserver$") = "codeserver"


class Helm(models.Helm, DeployablePatchedModelBase):
    type: constr(regex=r"^helm$") = "helm"


class Volume(models.Volume, DeployablePatchedModelBase):
    type: constr(regex=r"^volume$") = "volume"


class AsyncService(models.AsyncService, DeployablePatchedModelBase):
    type: constr(regex=r"^async-service$") = "async-service"
    replicas: Union[conint(ge=0, le=100), models.AsyncServiceAutoscaling] = 1
    resources: models.Resources = Field(default_factory=models.Resources)


class SSHServer(models.SSHServer, DeployablePatchedModelBase):
    type: constr(regex=r"^ssh-server$") = "ssh-server"


class Application(models.Application, DeployablePatchedModelBase):
    def deploy(self, workspace_fqn: str, wait: bool = True) -> Deployment:
        return deploy_component(
            component=self.__root__, workspace_fqn=workspace_fqn, wait=wait
        )
