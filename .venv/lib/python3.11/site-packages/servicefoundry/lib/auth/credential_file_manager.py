from __future__ import annotations

import os
import threading
from functools import lru_cache, wraps
from pathlib import Path
from typing import Optional

from filelock import FileLock, Timeout

from servicefoundry.lib.const import CREDENTIAL_FILEPATH
from servicefoundry.lib.model.entity import CredentialsFileContent
from servicefoundry.logger import logger


def _ensure_lock_taken(method):
    @wraps(method)
    def lock_guard(self, *method_args, **method_kwargs):
        if not self.lock_taken():
            raise Exception(
                "Trying to write to credential file without using with block"
            )
        return method(self, *method_args, **method_kwargs)

    return lock_guard


CRED_FILE_THREAD_LOCK = threading.RLock()


@lru_cache(maxsize=None)
def get_file_lock(lock_file_path: str) -> FileLock:
    return FileLock(lock_file_path)


class CredentialsFileManager:
    def __init__(
        self,
        credentials_file_path: Path = CREDENTIAL_FILEPATH,
        lock_timeout: float = 60.0,
    ) -> None:
        credentials_file_path = credentials_file_path.absolute()
        logger.debug("credential file path %r", credentials_file_path)

        credentials_lock_file_path = f"{credentials_file_path}.lock"
        logger.debug("credential lock file path %r", credentials_lock_file_path)

        self._credentials_file_path = credentials_file_path
        cred_file_dir = credentials_file_path.parent
        cred_file_dir.mkdir(exist_ok=True, parents=True)

        self._file_lock = get_file_lock(credentials_lock_file_path)
        self._lock_timeout = lock_timeout
        self._lock_owner: Optional[int] = None

    def __enter__(self) -> CredentialsFileManager:
        # The lock objects are recursive locks, which means that once acquired, they will not block on successive lock requests:
        lock_aquired = CRED_FILE_THREAD_LOCK.acquire(timeout=self._lock_timeout)
        if not lock_aquired:
            raise Exception(
                "Could not aquire CRED_FILE_THREAD_LOCK"
                f" in {self._lock_timeout} seconds"
            )
        try:
            self._file_lock.acquire(timeout=self._lock_timeout)
        except Timeout as ex:
            raise Exception(
                f"Failed to aquire lock on credential file within {self._lock_timeout} seconds.\n"
                "Is any other process trying to login?"
            ) from ex
        logger.debug("Acquired file and thread lock to access credential file")
        self._lock_owner = threading.get_ident()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self._file_lock.release()
        CRED_FILE_THREAD_LOCK.release()
        logger.debug("Released file and thread lock to access credential file")
        self._lock_owner = None

    def lock_taken(self) -> bool:
        return self._lock_owner == threading.get_ident()

    @_ensure_lock_taken
    def read(self) -> CredentialsFileContent:
        try:
            return CredentialsFileContent.parse_file(self._credentials_file_path)
        except Exception as ex:
            raise Exception(
                "Error while reading the credentials file "
                f"{self._credentials_file_path}. Please login again "
                "using `tfy login --relogin` or `tfy.login(relogin=True)` function"
            ) from ex

    @_ensure_lock_taken
    def write(self, credentials_file_content: CredentialsFileContent) -> None:
        if not isinstance(credentials_file_content, CredentialsFileContent):
            raise Exception(
                "Only object of type `CredentialsFileContent` is allowed. "
                f"Got {type(credentials_file_content)}"
            )
        logger.debug("Updating the credential file content")
        with open(self._credentials_file_path, "w", encoding="utf8") as file:
            file.write(credentials_file_content.json())

    @_ensure_lock_taken
    def delete(self) -> bool:
        if not os.path.exists(self._credentials_file_path):
            return False
        os.remove(self._credentials_file_path)
        return True

    @_ensure_lock_taken
    def exists(self) -> bool:
        return self._credentials_file_path.exists()
