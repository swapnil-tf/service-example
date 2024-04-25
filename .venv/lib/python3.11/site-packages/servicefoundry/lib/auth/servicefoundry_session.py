from __future__ import annotations

from typing import Optional

from servicefoundry.lib.auth.credential_provider import (
    CredentialProvider,
    EnvCredentialProvider,
    FileCredentialProvider,
)
from servicefoundry.lib.model.entity import UserInfo
from servicefoundry.logger import logger

ACTIVE_SESSION: Optional[ServiceFoundrySession] = None


class ServiceFoundrySession:
    def __init__(self) -> None:
        self._cred_provider = self._get_cred_provider()
        self._user_info: UserInfo = self._cred_provider.token.to_user_info()

        global ACTIVE_SESSION
        if (ACTIVE_SESSION is None) or (
            ACTIVE_SESSION
            and ACTIVE_SESSION.base_url != self.base_url
            and ACTIVE_SESSION.user_info != self.user_info
        ):
            logger.info(
                "Logged in to %r as %r (%s)",
                self.base_url,
                self.user_info.user_id,
                self.user_info.email or self.user_info.user_type.value,
            )
        ACTIVE_SESSION = self

    @staticmethod
    def _get_cred_provider() -> CredentialProvider:
        final_cred_provider = None
        for cred_provider in [EnvCredentialProvider, FileCredentialProvider]:
            if cred_provider.can_provide():
                final_cred_provider = cred_provider()
                break
        if final_cred_provider is None:
            raise Exception(
                "Please login again using `tfy login --relogin`"
                "or `tfy.login(relogin=True)` function"
            )
        return final_cred_provider

    @property
    def access_token(self) -> str:
        return self._cred_provider.token.access_token

    @property
    def base_url(self) -> str:
        return self._cred_provider.base_url

    @property
    def user_info(self) -> UserInfo:
        return self._user_info
