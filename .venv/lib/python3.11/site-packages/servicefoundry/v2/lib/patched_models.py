import enum
import re
import warnings
from collections.abc import Mapping
from typing import Optional, Union

from servicefoundry.auto_gen import models
from servicefoundry.pydantic_v1 import (
    BaseModel,
    Field,
    constr,
    root_validator,
    validator,
)

LEGACY_GPU_TYPE_COUNT_WARNING_MESSAGE_TEMPLATE = """
---------
The `gpu_count` and `gpu_type` fields are deprecated. Please remove these fields
from your deployment Python script or YAML Spec.

If you are using Python SDK, add GPUs in the following way:

```
from servicefoundry import NvidiaGPU, Resources
...

  resources=Resources(
    ...
    devices=[NvidiaGPU(name="{gpu_type}", count={gpu_count})],
  )
```

If you are using YAML Spec to deploy, add GPUs in the following way:

```
resources:
  devices:
    - type: nvidia_gpu
      name: {gpu_type}
      count: {gpu_count}
```
---------
"""

LEGACY_GPU_COUNT_WARNING_MESSAGE_TEMPLATE = """
---------
The `gpu_count` field is deprecated. Please remove this field from your
deployment Python script or YAML Spec.

If you are using Python SDK, add GPUs in the following way:

```
from servicefoundry import NvidiaGPU, Resources
...

  resources=Resources(
    ...
    devices=[NvidiaGPU(count={gpu_count})],
  )
```

If you are using YAML Spec to deploy, add GPUs in the following way:

```
resources:
  devices:
    - type: nvidia_gpu
      count: {gpu_count}
```
---------
"""


class CUDAVersion(str, enum.Enum):
    CUDA_11_0_CUDNN8 = "11.0-cudnn8"
    CUDA_11_1_CUDNN8 = "11.1-cudnn8"
    CUDA_11_2_CUDNN8 = "11.2-cudnn8"
    CUDA_11_3_CUDNN8 = "11.3-cudnn8"
    CUDA_11_4_CUDNN8 = "11.4-cudnn8"
    CUDA_11_5_CUDNN8 = "11.5-cudnn8"
    CUDA_11_6_CUDNN8 = "11.6-cudnn8"
    CUDA_11_7_CUDNN8 = "11.7-cudnn8"
    CUDA_11_8_CUDNN8 = "11.8-cudnn8"
    CUDA_12_0_CUDNN8 = "12.0-cudnn8"
    CUDA_12_1_CUDNN8 = "12.1-cudnn8"
    CUDA_12_2_CUDNN8 = "12.2-cudnn8"


class GPUType(str, enum.Enum):
    P4 = "P4"
    P100 = "P100"
    V100 = "V100"
    T4 = "T4"
    A10G = "A10G"
    A100_40GB = "A100_40GB"
    A100_80GB = "A100_80GB"
    L4 = "L4"


class AWSInferentiaAccelerator(str, enum.Enum):
    INF1 = "INF1"
    INF2 = "INF2"


class PatchedModelBase(BaseModel):
    class Config:
        extra = "forbid"


class DockerFileBuild(models.DockerFileBuild, PatchedModelBase):
    type: constr(regex=r"^dockerfile$") = "dockerfile"

    @validator("build_args")
    def validate_build_args(cls, value):
        if not isinstance(value, dict):
            raise TypeError("build_args should be of type dict")
        for k, v in value.items():
            if not isinstance(k, str) or not isinstance(v, str):
                raise TypeError("build_args should have keys and values as string")
            if not k.strip() or not v.strip():
                raise ValueError("build_args cannot have empty keys or values")
        return value


class PythonBuild(models.PythonBuild, PatchedModelBase):
    type: constr(regex=r"^tfy-python-buildpack$") = "tfy-python-buildpack"

    @root_validator
    def validate_python_version_when_cuda_version(cls, values):
        if values.get("cuda_version"):
            python_version = values.get("python_version")
            if python_version and not re.match(r"^3\.\d+$", python_version):
                raise ValueError(
                    f'`python_version` must be 3.x (e.g. "3.9") when `cuda_version` field is '
                    f"provided but got {python_version!r}. If you are adding a "
                    f'patch version, please remove it (e.g. "3.9.2" should be "3.9")'
                )
        return values


class RemoteSource(models.RemoteSource, PatchedModelBase):
    type: constr(regex=r"^remote$") = "remote"


class LocalSource(models.LocalSource, PatchedModelBase):
    type: constr(regex=r"^local$") = "local"


class Build(models.Build, PatchedModelBase):
    type: constr(regex=r"^build$") = "build"
    build_source: Union[
        models.RemoteSource, models.GitSource, models.LocalSource
    ] = Field(default_factory=LocalSource)


class Manual(models.Manual, PatchedModelBase):
    type: constr(regex=r"^manual$") = "manual"


class Schedule(models.Schedule, PatchedModelBase):
    type: constr(regex=r"^scheduled$") = "scheduled"


class GitSource(models.GitSource, PatchedModelBase):
    type: constr(regex=r"^git$") = "git"


class HttpProbe(models.HttpProbe, PatchedModelBase):
    type: constr(regex=r"^http$") = "http"


class BasicAuthCreds(models.BasicAuthCreds, PatchedModelBase):
    type: constr(regex=r"^basic_auth$") = "basic_auth"


class HealthProbe(models.HealthProbe, PatchedModelBase):
    pass


class Image(models.Image, PatchedModelBase):
    type: constr(regex=r"^image$") = "image"


class Port(models.Port, PatchedModelBase):
    pass

    @root_validator(pre=True)
    def verify_host(cls, values):
        expose = values.get("expose", True)
        host = values.get("host", None)
        if expose:
            if not host:
                raise ValueError("Host must be provided to expose port")
            if not (
                re.fullmatch(
                    r"^((([a-zA-Z0-9\-]{1,63}\.)([a-zA-Z0-9\-]{1,63}\.)*([A-Za-z]{1,63}))|(((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)))$",
                    host,
                )
            ):
                raise ValueError(
                    "Invalid value for `host`. A valid host must contain only alphanumeric letters and hypens e.g.  `ai.example.com`, `app.truefoundry.com`.\nYou can get the list of configured hosts for the cluster from the Integrations > Clusters page. Please see https://docs.truefoundry.com/docs/checking-configured-domain for more information."
                )
        else:
            if host:
                raise ValueError("Cannot pass host when expose=False")

        return values


class Resources(models.Resources, PatchedModelBase):
    @root_validator(pre=False)
    def warn_gpu_count_type_depreciation(cls, values):
        gpu_count = values.get("gpu_count")
        gpu_type = None
        node = values.get("node")
        if node:
            if isinstance(node, NodeSelector):
                gpu_type = node.gpu_type
            elif isinstance(node, Mapping):
                gpu_count = node.get("gpu_type")

        if gpu_count and gpu_type:
            warnings.warn(
                LEGACY_GPU_TYPE_COUNT_WARNING_MESSAGE_TEMPLATE.format(
                    gpu_type=gpu_type,
                    gpu_count=gpu_count,
                ),
                category=FutureWarning,
                stacklevel=2,
            )
        elif gpu_count:
            warnings.warn(
                LEGACY_GPU_COUNT_WARNING_MESSAGE_TEMPLATE.format(
                    gpu_count=gpu_count,
                ),
                category=FutureWarning,
                stacklevel=2,
            )
        return values


class Param(models.Param, PatchedModelBase):
    pass


class CPUUtilizationMetric(models.CPUUtilizationMetric, PatchedModelBase):
    type: constr(regex=r"^cpu_utilization$") = "cpu_utilization"


class RPSMetric(models.RPSMetric, PatchedModelBase):
    type: constr(regex=r"^rps$") = "rps"


class CronMetric(models.CronMetric, PatchedModelBase):
    type: constr(regex=r"^cron$") = "cron"


class ServiceAutoscaling(models.ServiceAutoscaling, PatchedModelBase):
    pass


class AsyncServiceAutoscaling(models.AsyncServiceAutoscaling, PatchedModelBase):
    pass


class Autoscaling(ServiceAutoscaling):
    def __init__(self, **kwargs):
        warnings.warn(
            "`servicefoundry.Autoscaling` is deprecated and will be removed in a future version. "
            "Please use `servicefoundry.ServiceAutoscaling` instead. "
            "You can rename `Autoscaling` to `ServiceAutoscaling` in your script.",
            category=DeprecationWarning,
            stacklevel=2,
        )
        super().__init__(**kwargs)


class BlueGreen(models.BlueGreen, PatchedModelBase):
    type: constr(regex=r"^blue_green$") = "blue_green"


class Canary(models.Canary, PatchedModelBase):
    type: constr(regex=r"^canary$") = "canary"


class Rolling(models.Rolling, PatchedModelBase):
    type: constr(regex=r"^rolling_update$") = "rolling_update"


class SecretMount(models.SecretMount, PatchedModelBase):
    type: constr(regex=r"^secret$") = "secret"


class StringDataMount(models.StringDataMount, PatchedModelBase):
    type: constr(regex=r"^string$") = "string"


class VolumeMount(models.VolumeMount, PatchedModelBase):
    type: constr(regex=r"^volume$") = "volume"


class NodeSelector(models.NodeSelector, PatchedModelBase):
    type: constr(regex=r"^node_selector$") = "node_selector"
    gpu_type: Optional[Union[GPUType, str]] = None


class NodepoolSelector(models.NodepoolSelector, PatchedModelBase):
    type: constr(regex=r"^nodepool_selector$") = "nodepool_selector"


class Endpoint(models.Endpoint, PatchedModelBase):
    pass


class TruefoundryImageBase(models.TruefoundryImageBase, PatchedModelBase):
    type: constr(regex=r"^truefoundrybase$") = "truefoundrybase"


class TruefoundryImageFull(models.TruefoundryImageFull, PatchedModelBase):
    type: constr(regex=r"^truefoundryfull$") = "truefoundryfull"


class CodeserverImage(models.CodeserverImage, PatchedModelBase):
    type: constr(regex=r"^codeserver$") = "codeserver"


class HelmRepo(models.HelmRepo, PatchedModelBase):
    type: constr(regex=r"^helm-repo$") = "helm-repo"


class OCIRepo(models.OCIRepo, PatchedModelBase):
    type: constr(regex=r"^oci-repo$") = "oci-repo"


class VolumeBrowser(models.VolumeBrowser, PatchedModelBase):
    pass


class WorkerConfig(models.WorkerConfig, PatchedModelBase):
    pass


class SQSInputConfig(models.SQSInputConfig, PatchedModelBase):
    type: constr(regex=r"^sqs$") = "sqs"


class SQSOutputConfig(models.SQSOutputConfig, PatchedModelBase):
    type: constr(regex=r"^sqs$") = "sqs"


class SQSQueueMetricConfig(models.SQSQueueMetricConfig, PatchedModelBase):
    type: constr(regex=r"^sqs$") = "sqs"


class AWSAccessKeyAuth(models.AWSAccessKeyAuth, PatchedModelBase):
    pass


class NATSInputConfig(models.NATSInputConfig, PatchedModelBase):
    type: constr(regex=r"^nats$") = "nats"


class CoreNATSOutputConfig(models.CoreNATSOutputConfig, PatchedModelBase):
    type: constr(regex=r"^core-nats$") = "core-nats"


class NATSUserPasswordAuth(models.NATSUserPasswordAuth, PatchedModelBase):
    pass


class NATSOutputConfig(models.NATSOutputConfig, PatchedModelBase):
    type: constr(regex=r"^nats$") = "nats"


class NATSMetricConfig(models.NATSMetricConfig, PatchedModelBase):
    type: constr(regex=r"^nats$") = "nats"


class KafkaInputConfig(models.KafkaInputConfig, PatchedModelBase):
    type: constr(regex=r"^kafka$") = "kafka"


class KafkaOutputConfig(models.KafkaOutputConfig, PatchedModelBase):
    type: constr(regex=r"^kafka$") = "kafka"


class KafkaMetricConfig(models.KafkaMetricConfig, PatchedModelBase):
    type: constr(regex=r"^kafka$") = "kafka"


class KafkaSASLAuth(models.KafkaSASLAuth, PatchedModelBase):
    pass


class AMQPInputConfig(models.AMQPInputConfig, PatchedModelBase):
    type: constr(regex=r"^amqp$") = "amqp"


class AMQPOutputConfig(models.AMQPOutputConfig, PatchedModelBase):
    type: constr(regex=r"^amqp$") = "amqp"


class AMQPMetricConfig(models.AMQPMetricConfig, PatchedModelBase):
    type: constr(regex=r"^amqp$") = "amqp"


class AsyncProcessorSidecar(models.AsyncProcessorSidecar, PatchedModelBase):
    pass


class ArtifactsCacheVolume(models.ArtifactsCacheVolume, PatchedModelBase):
    pass


class HuggingfaceArtifactSource(models.HuggingfaceArtifactSource, PatchedModelBase):
    type: constr(regex=r"^huggingface-hub$") = "huggingface-hub"


class TruefoundryArtifactSource(models.TruefoundryArtifactSource, PatchedModelBase):
    type: constr(regex=r"^truefoundry-artifact$") = "truefoundry-artifact"


class ArtifactsDownload(models.ArtifactsDownload, PatchedModelBase):
    pass


class CustomNotebookImage(models.CustomNotebookImage, PatchedModelBase):
    type: constr(regex=r"^customnotebook$") = "customnotebook"


class NvidiaGPU(models.NvidiaGPU, PatchedModelBase):
    type: constr(regex=r"^nvidia_gpu$") = "nvidia_gpu"
    name: Optional[Union[GPUType, str]] = None


class NvidiaMIGGPU(models.NvidiaMIGGPU, PatchedModelBase):
    type: constr(regex=r"^nvidia_mig_gpu$") = "nvidia_mig_gpu"


class NvidiaTimeslicingGPU(models.NvidiaTimeslicingGPU, PatchedModelBase):
    type: constr(regex=r"^nvidia_timeslicing_gpu$") = "nvidia_timeslicing_gpu"


class AWSInferentia(models.AWSInferentia, PatchedModelBase):
    type: constr(regex=r"^aws_inferentia$") = "aws_inferentia"
    name: Optional[Union[AWSInferentiaAccelerator, str]] = None


class CustomCodeserverImage(models.CustomCodeserverImage, PatchedModelBase):
    type: constr(regex=r"^customcodeserver$") = "customcodeserver"


class CustomSSHServerImage(models.CustomSSHServerImage, PatchedModelBase):
    type: constr(regex=r"^custom-ssh-server$") = "custom-ssh-server"


class SSHServerImage(models.SSHServerImage, PatchedModelBase):
    type: constr(regex=r"^ssh-server") = "ssh-server"


class TruefoundryImageCuda1180(models.TruefoundryImageCuda1180, PatchedModelBase):
    type: constr(regex=r"^truefoundrycuda1180$") = "truefoundrycuda1180"


class TruefoundryImageCuda1211(models.TruefoundryImageCuda1211, PatchedModelBase):
    type: constr(regex=r"^truefoundrycuda1211$") = "truefoundrycuda1211"


class DynamicVolumeConfig(models.DynamicVolumeConfig, PatchedModelBase):
    type: constr(regex=r"^dynamic$") = "dynamic"


class StaticVolumeConfig(models.StaticVolumeConfig, PatchedModelBase):
    type: constr(regex=r"^static$") = "static"
