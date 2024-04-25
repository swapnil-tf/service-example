import argparse
import logging

from servicefoundry import Build, PythonBuild, Resources, Service

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("--workspace-fqn", type=str, required=True)
args = parser.parse_args()

service = Service(
    # name="my-service",
    name="my-service-1",
    image=Build(
        build_spec=PythonBuild(
            command="uvicorn main:app --port 4000 --host 0.0.0.0",
            pip_packages=[
                "fastapi",
                "uvicorn",
            ],
            python_version="3.9",
        ),
    ),
    ports=[{"expose": True, "port": 4000}],
    replicas=2,
    resources=Resources(cpu_limit=0.6),
)
deployment = service.deploy(workspace_fqn=args.workspace_fqn)
