import time

import requests

from servicefoundry.lib.clients.utils import poll_for_function, request_handling
from servicefoundry.lib.const import VERSION_PREFIX
from servicefoundry.lib.exceptions import BadRequestException
from servicefoundry.lib.model.entity import DeviceCode, Token
from servicefoundry.logger import logger


class AuthServiceClient:
    def __init__(self, base_url):
        from servicefoundry.lib.clients.service_foundry_client import (
            ServiceFoundryServiceClient,
        )

        client = ServiceFoundryServiceClient(init_session=False, base_url=base_url)
        tenant_info = client.get_tenant_info()

        self._auth_server_url = tenant_info.auth_server_url
        self._tenant_name = tenant_info.tenant_name

    def refresh_token(self, token: Token, host: str = None) -> Token:
        host_arg_str = f"--host {host}" if host else "--host HOST"
        if not token.refresh_token:
            # TODO: Add a way to propagate error messages without traceback to the output interface side
            raise Exception(
                f"Unable to resume login session. Please log in again using `tfy login {host_arg_str} --relogin`"
            )
        url = f"{self._auth_server_url}/api/{VERSION_PREFIX}/oauth/token/refresh"
        data = {
            "tenantName": token.tenant_name,
            "refreshToken": token.refresh_token,
        }
        res = requests.post(url, data=data)
        try:
            res = request_handling(res)
            return Token.parse_obj(res)
        except BadRequestException as ex:
            raise Exception(
                f"Unable to resume login session. Please log in again using `tfy login {host_arg_str} --relogin`"
            ) from ex

    def get_device_code(self) -> DeviceCode:
        url = f"{self._auth_server_url}/api/{VERSION_PREFIX}/oauth/device"
        data = {"tenantName": self._tenant_name}
        res = requests.post(url, data=data)
        res = request_handling(res)
        return DeviceCode.parse_obj(res)

    def get_token_from_device_code(
        self, device_code: str, timeout: float = 60
    ) -> Token:
        url = f"{self._auth_server_url}/api/{VERSION_PREFIX}/oauth/device/token"
        data = {
            "tenantName": self._tenant_name,
            "deviceCode": device_code,
        }
        start_time = time.monotonic()
        poll_interval_seconds = 1

        for response in poll_for_function(
            requests.post, poll_after_secs=poll_interval_seconds, url=url, data=data
        ):
            if response.status_code == 201:
                response = response.json()
                return Token.parse_obj(response)
            elif response.status_code == 202:
                logger.debug("User has not authorized yet. Checking again.")
            else:
                raise Exception(
                    "Failed to get token using device code. "
                    f"status_code {response.status_code},\n {response.text}"
                )
            time_elapsed = time.monotonic() - start_time
            if time_elapsed > timeout:
                logger.warning("Polled server for %s secs.", int(time_elapsed))
                break

        raise Exception(f"Did not get authorized within {timeout} seconds.")
