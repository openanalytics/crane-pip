# TODO refactor this whole page

import datetime
import json
import os
import sys
import time
from pathlib import Path
from pprint import pprint
from typing import Literal

import urllib3


class Auth:
    """Class implementing the device login flow of OAuth.
    Used for authenticating against a crane"""

    # TODO have _init by configured based on the index configured
    def __init__(self, index_url: str):
        "Index url to authenticate against"
        # TODO read client_id from cached directory
        self.client_id = "pip"

        # TODO update with https://github.com/platformdirs/platformdirs to be platfrom independed.
        self.dirname = os.path.join(Path.home(), ".cache", "crane-pip")
        os.makedirs(self.dirname, exist_ok=True)

        # TODO specify how the user should configure these urls or how discover them from a given openid-configuration url.
        # TODO replace this with cache look up.
        self.device_code_url = os.environ["CRANE_DEVICE_URL"].strip()
        self.token_url = os.environ["CRANE_TOKEN_URL"].strip()

        # TODO use the same.
        self.filename = os.path.join(self.dirname, "auth_crane.json")

        self._current_request_device_code = None
        self._current_request_interval = 5

        # tokens
        self._current_refresh_token: str
        self._current_refresh_token_not_after: datetime.datetime
        self._current_access_token: str
        self._current_access_token_not_after: datetime.datetime

    def authenticate(self) -> Literal[True]:
        """Perform the authentication flow

        1. Check for cached token.
        2. If no cache found -> Perform device code request which requires user interaction.
        """

        # TODO crash with proper Exception errors and just prints.
        if self._read_cache():
            # loaded tokens form cache
            return True

        if not self._device_code_request():
            print("Device code request failed")
            sys.exit(1)

        if not self._start_polling():
            print("Polling request failed")
            sys.exit(1)

        self._cache_tokens()
        return True

    def get_access_token(self) -> str:
        "Fetch the access token to use in authentication with the crane server."
        self._refresh_access_token_if_required()
        return self._current_access_token

    def _refresh_access_token_if_required(self) -> None:
        """Refresh the access token if expired.
        An Exception is raised if the refresh token is also already expired."""

        # TODO add check if the refresh token is also not expired!
        if self._current_access_token_not_after < datetime.datetime.now():
            self._refresh_access_token()
            self._cache_tokens()

    def _read_cache(self) -> bool:
        """Attempt to fetch tokens from cache.

        If succeeded, TRUE is returned and `get_access_token()` can get used to fetch the token.
        If did not succeed the user will need to perform the device code login flow.

        Incase the access_token is invalid but the refresh token is still valid. Then tokens are
        automatically refreshed.
        """
        if not os.path.exists(self.filename):
            return False
        with open(self.filename, "r") as fh:
            cache = json.load(fh)
            if "refresh_token" not in cache or "refresh_token_not_after" not in cache:
                return False
            # check refresh token still valid for at least 5 minutes
            not_after = datetime.datetime.now() + datetime.timedelta(minutes=5)
            refresh_token_not_after = datetime.datetime.fromtimestamp(
                cache["refresh_token_not_after"]
            )
            if refresh_token_not_after < not_after:
                return False

            self._current_refresh_token = cache["refresh_token"]
            self._current_refresh_token_not_after = datetime.datetime.fromtimestamp(
                cache["refresh_token_not_after"]
            )

            # check access token still valid
            if "access_token" in cache and "access_token_not_after" in cache:
                access_token_not_after = datetime.datetime.fromtimestamp(
                    cache["access_token_not_after"]
                )
                if access_token_not_after > datetime.datetime.now():
                    self._current_access_token = cache["access_token"]
                    self._current_access_token_not_after = access_token_not_after

                    # TODO have this be formally with logging
                    print("You are now authenticated.")
                    return True

            # If refresh token did not expire yet. But the access token did. Then refresh tokens.
            if not self._refresh_access_token():
                return False
            self._cache_tokens()
            return True

    def _device_code_request(self) -> bool:
        """Initiate a device code login fow.

        On success true is returned and the user will now need to perform
        authentication on the device.

        Start checking if the user has logged-id via _start_polling.
        """
        payload = {"client_id": self.client_id, "scope": "openid offline_access"}

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = urllib3.request(
            method="POST",
            url=self.device_code_url,
            headers=headers,
            body=json.dumps(payload),
        )
        content = response.json()

        if content is None or "error" in content:
            # TODO make proper error here
            print(content)
            return False

        self._current_request_device_code = content["device_code"]
        if "interval" in content:
            self._current_request_interval = content["interval"]

        print("------------------------------")
        print("Please authenticate:")
        print(f"\tpoint your browser to: {content['verification_uri']}")
        print(f"\tand enter your user code: {content['user_code']}")
        if "verification_uri_complete" in content:
            print(f"\tor use the direct link: {content['verification_uri_complete']}")
        print("------------------------------" "")
        return True

    def _start_polling(self) -> bool:
        """Blocking call that waits until the user performed the login.

        On success, True is returned and the tokens are acquired and stored in the object.
        The tokens still need to be stored in the cache, if desired, by calling the _cache_tokens
        """
        print("Waiting for authentication.", sep="", end="", flush=True)
        while True:
            time.sleep(self._current_request_interval)
            print(".", sep="", end="", flush=True)

            payload = {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": self._current_request_device_code,
                "client_id": self.client_id,
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = urllib3.request(
                method="POST",
                url=self.device_code_url,
                headers=headers,
                body=json.dumps(payload),
            )
            content = response.json()

            if content is None:
                # TODO make into exception
                pprint(response)
                return False

            if "error" in content:
                if content["error"] == "authorization_pending":
                    continue
                else:
                    pprint(content)
                    return False

            now = datetime.datetime.now()

            self._current_access_token = content["access_token"]
            self._current_refresh_token = content["refresh_token"]
            self._current_access_token_not_after = now + datetime.timedelta(
                seconds=content["expires_in"]
            )
            self._current_refresh_token_not_after = now + datetime.timedelta(
                seconds=content["refresh_expires_in"]
            )

            print()
            print("You are now authenticated.")
            return True

    def _refresh_access_token(self) -> bool:
        """Refresh the access and refresh token and store in cache. Return True on success.

        Note, tokens are not cached yet. They are simply stored in the object. Call _cache_tokens
        to cache.
        """
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self._current_refresh_token,
            "client_id": self.client_id,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = urllib3.request(
            method="POST",
            url=self.device_code_url,
            headers=headers,
            body=json.dumps(payload),
        )
        content = response.json()
        if content is None or "error" in content:
            return False

        now = datetime.datetime.now()

        self._current_access_token = content["access_token"]
        self._current_refresh_token = content["refresh_token"]
        self._current_access_token_not_after = now + datetime.timedelta(
            seconds=content["expires_in"]
        )
        self._current_refresh_token_not_after = now + datetime.timedelta(
            seconds=content["refresh_expires_in"]
        )

        print("You are now authenticated.")
        return True

    def _cache_tokens(self) -> None:
        "Cache the currently stored tokens"

        # TODO add check if tokens are loaded in the first place.
        cache = {
            "refresh_token": self._current_refresh_token,
            "refresh_token_not_after": self._current_refresh_token_not_after.timestamp(),
            "access_token": self._current_access_token,
            "access_token_not_after": self._current_access_token_not_after.timestamp(),
        }
        with open(self.filename, "w") as fh:
            fh.write(json.dumps(cache))
        os.chmod(self.dirname, 0o700)
        os.chmod(self.filename, 0o600)
