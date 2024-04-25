import argparse
import logging

from servicefoundry import ModelDeployment, Resources, TruefoundryModelRegistry

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("--workspace-fqn", type=str, required=True)
parser.add_argument("--model-fqn", type=str, required=True)
args = parser.parse_args()

service = ModelDeployment(
    name="from-cli-mlf",
    model_source=TruefoundryModelRegistry(model_version_fqn=args.model_fqn),
    resources=Resources(cpu_limit=1.0, memory_limit=600),
)
service.deploy(workspace_fqn=args.workspace_fqn)
