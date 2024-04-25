import os

DEBUG = os.getenv("AUTODEPLOY_DEBUG", "")

AUTODEPLOY_TFY_BASE_URL = os.getenv(
    "AUTODEPLOY_TFY_BASE_URL", "https://app.truefoundry.com"
).strip("/")
AUTODEPLOY_OPENAI_BASE_URL = os.environ.get("AUTODEPLOY_OPENAI_BASE_URL")
AUTODEPLOY_OPENAI_API_KEY = os.environ.get("AUTODEPLOY_OPENAI_API_KEY")
AUTODEPLOY_MODEL_NAME = os.environ.get(
    "AUTODEPLOY_MODEL_NAME", "auto-deploy-openai/gpt-4-turbo-2024-04-09"
)
AUTODEPLOY_INTRO_MESSAGE = """Truefoundry will first check for a [blue]Dockerfile[/] in your project.
If it's not present, Truefoundry will generate one for you.
Then, it will attempt to build a Docker image on your machine.
If any issues are encountered during this process, Truefoundry will attempt to automatically fix them.
Finally, it will run the application to verify that everything is set up correctly.
"""
ABOUT_AUTODEPLOY = """To deploy your project, we will generate the deployment configuration using AI.
We will analyze your codebase using our AI agent and make the required changes so that we can build and deploy the code.
We will confirm all the changes with you.
"""
