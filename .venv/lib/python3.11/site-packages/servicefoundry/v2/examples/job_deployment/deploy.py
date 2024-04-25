import logging

from servicefoundry import Build, Job, PythonBuild, Schedule

logging.basicConfig(level=logging.INFO)

job = Job(
    name="my-job-manual",
    image=Build(
        build_spec=PythonBuild(command="python main.py --upto 30"),
    ),
)
job.deploy(workspace_fqn="v1:local:my-ws-2")


job = Job(
    name="my-job-sch",
    image=Build(
        build_spec=PythonBuild(command="python main.py --upto 30"),
    ),
    trigger=Schedule(schedule="*/60 * * * *"),
)
job.deploy(workspace_fqn="v1:local:my-ws-2")
