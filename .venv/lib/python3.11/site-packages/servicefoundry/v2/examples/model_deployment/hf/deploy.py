import argparse
import logging

from servicefoundry import HuggingfaceModelHub, ModelDeployment, Resources

logging.basicConfig(level=logging.INFO)

parser = argparse.ArgumentParser()
parser.add_argument("--workspace-fqn", type=str, required=True)
parser.add_argument("--model-id", type=str, required=True)
parser.add_argument("--pipeline", type=str, default=None)
args = parser.parse_args()

service = ModelDeployment(
    name="from-cli-hf",
    model_source=HuggingfaceModelHub(model_id=args.model_id, pipeline=args.pipeline),
    resources=Resources(cpu_limit=1.0, memory_limit=600),
)
service.deploy(workspace_fqn=args.workspace_fqn)
