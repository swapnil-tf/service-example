import subprocess

from servicefoundry.logger import logger


class Shell:
    def execute_shell_command(self, command, ip=None):
        logger.debug(f"executing command: {command}")
        try:
            p = subprocess.run(command, stdout=subprocess.PIPE, check=True, input=ip)
            return p.stdout.decode("UTF-8")
        except subprocess.CalledProcessError as err:
            raise Exception(f"failed to execute: {command}, error: {err}")
