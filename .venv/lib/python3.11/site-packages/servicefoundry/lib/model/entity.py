from __future__ import annotations

import datetime
import time
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import jwt

from servicefoundry.lib.util import get_application_fqn_from_deployment_fqn
from servicefoundry.pydantic_v1 import BaseModel, Extra, Field, constr, validator

# TODO: switch to Enums for str literals
# TODO: Need a better approach to keep fields in sync with server
#       most fields should have a default in case server adds/removes a field
# TODO: Implement NotImplementedError sections
UNDEFINED_STRING = "<Undefined>"


class Base(BaseModel):
    class Config:
        validate_assignment = True
        use_enum_values = True
        extra = Extra.allow

    def __repr_args__(self):
        return [
            (key, value)
            for key, value in self.__dict__.items()
            if key in self.__fields__
            and self.__fields__[key].field_info.extra.get("repr", True)
        ]


class Entity(Base):
    createdAt: datetime.datetime = Field(repr=False)
    updatedAt: datetime.datetime = Field(repr=False)
    createdBy: str = Field(repr=False)


class Workspace(Entity):
    id: str = Field(repr=False)
    name: str
    fqn: str
    clusterId: str = Field(repr=False)

    def list_row_data(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "fqn": self.fqn,
            "cluster_fqn": self.clusterId,
            "created_at": self.createdAt,
        }

    def get_data(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "fqn": self.fqn,
            "cluster_fqn": self.clusterId,
            "created_at": self.createdAt,
            "updated_at": self.updatedAt,
            "created_by": self.createdBy,
        }


class WorkspaceResources(BaseModel):
    cpu_limit: Optional[float]
    memory_limit: Optional[int]
    ephemeral_storage_limit: Optional[int]


class PortMetadata(BaseModel):
    port: int
    # TODO: done because of a bug, needs to reverted to be mandatory
    host: Optional[str]


class DeploymentTransitionStatus(str, Enum):
    INITIALIZED: str = "INITIALIZED"
    BUILDING: str = "BUILDING"
    DEPLOYING: str = "DEPLOYING"
    BUILD_SUCCESS: str = "BUILD_SUCCESS"
    DEPLOY_SUCCESS: str = "DEPLOY_SUCCESS"
    DEPLOY_FAILED: str = "DEPLOY_FAILED"
    BUILD_FAILED: str = "BUILD_FAILED"
    CANCELLED: str = "CANCELLED"
    FAILED: str = "FAILED"
    REUSING_EXISTING_BUILD: str = "REUSING_EXISTING_BUILD"
    REDEPLOY_STARTED: str = "REDEPLOY_STARTED"
    PAUSED: str = "PAUSED"
    ROLLOUT_STARTED: str = "ROLLOUT_STARTED"
    SET_TRAFFIC: str = "SET_TRAFFIC"
    DEPLOY_FAILED_WITH_RETRY: str = "DEPLOY_FAILED_WITH_RETRY"
    WAITING: str = "WAITING"

    _: str = ""

    @classmethod
    def is_failure_state(cls, state: DeploymentTransitionStatus) -> bool:
        return state in (cls.DEPLOY_FAILED, cls.BUILD_FAILED, cls.FAILED, cls.CANCELLED)


class DeploymentState(BaseModel):
    isTerminalState: bool


class DeploymentStatus(BaseModel):
    state: DeploymentState
    status: DeploymentTransitionStatus
    transition: Optional[DeploymentTransitionStatus]


class DeploymentManifest(Base):
    name: Optional[str] = Field(default=UNDEFINED_STRING)
    type: str


class Deployment(Entity):
    id: str = Field(repr=False)
    fqn: str
    version: int
    currentStatusId: str = Field(repr=False)
    applicationId: str = Field(repr=False)
    manifest: DeploymentManifest = Field(repr=False)
    failureReason: Optional[str]
    deploymentStatuses: Optional[List[DeploymentStatus]]
    metadata: Optional[
        Union[Dict[str, Any], List[Dict[str, Any]]]
    ]  # TODO (chiragjn): revisit the type of this field
    currentStatus: Optional[DeploymentStatus]  # Server was not returning CurrentStatus
    application_fqn: str

    def __init__(self, **kwargs) -> None:
        deployment_fqn = kwargs.get("fqn")
        if not deployment_fqn:
            raise ValueError("'fqn' field is required")
        application_fqn = ":".join(deployment_fqn.split(":")[:3])
        kwargs["application_fqn"] = application_fqn
        return super().__init__(**kwargs)

    @property
    def application_fqn(self) -> str:
        return get_application_fqn_from_deployment_fqn(self.fqn)

    def list_row_data(self) -> Dict[str, Any]:
        return {
            "fqn": self.fqn,
            "application_name": self.manifest.name,
            "version": self.version,
            "created_at": self.createdAt,
        }

    def get_data(self) -> Dict[str, Any]:
        # TODO: Remove this splitting logic
        cluster_fqn, workspace_name, *_ = self.fqn.split(":")
        workspace_fqn = ":".join([cluster_fqn, workspace_name])
        return {
            "fqn": self.fqn,
            "application_name": self.manifest.name,
            "application_type": self.manifest.type,
            "version": self.version,
            "workspace_fqn": workspace_fqn,
            "cluster_fqn": cluster_fqn,
            "created_at": self.createdAt,
            "updated_at": self.updatedAt,
            "created_by": self.createdBy,
        }

    class Config:
        extra = Extra.allow


class ApplicationWorkspace(Base):
    name: str
    fqn: str
    clusterId: str


class Application(Entity):
    id: str = Field(repr=False)
    name: str
    fqn: str
    tenantName: str
    workspaceId: str = Field(repr=False)
    lastVersion: int
    activeVersion: int
    workspace: ApplicationWorkspace
    deployment: Deployment
    activeDeploymentId: Optional[str] = Field(repr=False)
    lastDeploymentId: str = Field(repr=False)

    def list_row_data(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.deployment.manifest.type,
            "fqn": self.fqn,
            "active_version": self.activeVersion,
            "workspace_name": self.workspace.name,
            "created_at": self.createdAt,
        }

    def get_data(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.deployment.manifest.type,
            "fqn": self.fqn,
            "active_version": self.activeVersion,
            "last_version": self.lastVersion,
            "workspace_fqn": self.workspace.fqn,
            "cluster_fqn": self.workspace.clusterId,
            "created_at": self.createdAt,
            "updated_at": self.updatedAt,
            "created_by": self.createdBy,
        }


class UserType(Enum):
    user = "user"
    serviceaccount = "serviceaccount"


class UserInfo(BaseModel):
    user_id: constr(min_length=1)
    user_type: UserType = UserType.user
    email: Optional[str] = None
    tenant_name: constr(min_length=1) = Field(alias="tenantName")

    class Config:
        allow_population_by_field_name = True
        allow_mutation = False


class TenantInfo(BaseModel):
    tenant_name: constr(min_length=1) = Field(alias="tenantName")
    auth_server_url: str

    class Config:
        allow_population_by_field_name = True
        allow_mutation = False


class Token(BaseModel):
    access_token: constr(min_length=1) = Field(alias="accessToken", repr=False)
    refresh_token: Optional[constr(min_length=1)] = Field(
        alias="refreshToken", repr=False
    )
    decoded_value: Optional[Dict] = Field(exclude=True, repr=False)

    class Config:
        allow_population_by_field_name = True
        allow_mutation = False

    @validator("decoded_value", always=True, pre=True)
    def _decode_jwt(cls, v, values, **kwargs):
        access_token = values["access_token"]
        return jwt.decode(
            access_token,
            options={
                "verify_signature": False,
                "verify_aud": False,
                "verify_exp": False,
            },
        )

    @property
    def tenant_name(self) -> str:
        return self.decoded_value["tenantName"]

    def is_going_to_be_expired(self, buffer_in_seconds: int = 120) -> bool:
        exp = int(self.decoded_value["exp"])
        return (exp - time.time()) < buffer_in_seconds

    def to_user_info(self) -> UserInfo:
        return UserInfo(
            user_id=self.decoded_value["username"],
            email=self.decoded_value["email"]
            if "email" in self.decoded_value
            else None,
            user_type=UserType(self.decoded_value.get("userType", UserType.user.value)),
            tenant_name=self.tenant_name,
        )


class CredentialsFileContent(BaseModel):
    access_token: constr(min_length=1) = Field(repr=False)
    refresh_token: Optional[constr(min_length=1)] = Field(repr=False)
    host: constr(min_length=1)

    class Config:
        allow_mutation = False

    def to_token(self) -> Token:
        return Token(access_token=self.access_token, refresh_token=self.refresh_token)


class DeviceCode(BaseModel):
    user_code: str = Field(alias="userCode")
    device_code: str = Field(alias="deviceCode")

    class Config:
        allow_population_by_field_name = True
        allow_mutation = False

    def get_user_clickable_url(self, auth_host: str) -> str:
        return f"{auth_host}/authorize/device?userCode={self.user_code}"


class JobRun(Base):
    name: str
    applicationName: str
    deploymentVersion: int
    createdAt: int
    endTime: Optional[int] = None
    duration: Optional[str] = None
    command: str
    totalRetries: Optional[int] = 0
    status: str

    def list_row_data(self) -> Dict[str, Any]:
        from servicefoundry.cli.display_util import display_time_passed

        triggered_at = (
            (datetime.datetime.now().timestamp() * 1000) - self.createdAt
        ) // 1000
        triggered_at = f"{display_time_passed(triggered_at)} ago"
        duration = ""
        if self.duration:
            duration = display_time_passed(int(float(self.duration)))
        return {
            "name": self.name,
            "deployment_version": self.deploymentVersion,
            "status": self.status,
            "triggered_at": triggered_at,
            "duration": duration,
        }

    def get_data(self) -> Dict[str, Any]:
        from servicefoundry.cli.display_util import display_time_passed

        created_at = datetime.datetime.fromtimestamp(self.createdAt // 1000)
        end_time = ""
        if self.endTime:
            end_time = datetime.datetime.fromtimestamp(self.endTime // 1000)
        duration = ""
        if self.duration:
            duration = display_time_passed(int(float(self.duration)))
        return {
            "name": self.name,
            "application_name": self.applicationName,
            "deployment_version": self.deploymentVersion,
            "created_at": created_at,
            "end_time": end_time,
            "duration": duration,
            "command": self.command,
            "status": self.status,
        }


class TriggerJobResult(Base):
    message: str = Field(default="Unknown")
    jobRunName: str = Field(default=None)


class DockerRegistryCredentials(Base):
    fqn: str
    registryUrl: str
    username: str
    password: str


class CreateDockerRepositoryResponse(Base):
    repoName: str
