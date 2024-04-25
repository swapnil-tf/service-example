import logging

from my_module import normal, uniform

from servicefoundry import Resources
from servicefoundry.function_service import BuildConfig, FunctionService

logging.basicConfig(level=logging.INFO)

random_service = FunctionService(
    name="random-service-2",
    build_config=BuildConfig(pip_packages=["numpy<1.22.0"]),
    resources=Resources(cpu_limit=0.5, memory_limit=512),
    replicas=2,
    port=4000,
)
random_service.register_function(normal)
random_service.register_function(uniform)

print(random_service)
# random_service.deploy("v1:local:my-ws-2")
random_service.run().join()
