# Second attempt
from datetime import datetime
import os
import json
import time
from pathlib import Path
from typing import Dict, TypedDict, Union

import urllib3


###### Crane config:

CONFIG_DIR = os.path.join(Path.home(), ".local", "share", "crane", "python")
os.makedirs(CONFIG_DIR, exists_ok=True)

CONFIG_FILE = os.path.join(CONFIG_DIR, "index_config.json")


class CraneIndexConfig(TypedDict):
    "Crane configuration for a single index."

    client_id: str
    token_url: str
    device_code_url: str


class CraneConfig:
    "Crane configuration for all the indexes"

    def __init__(self) -> None:
        # Key = index urls
        self._config: Dict[str, CraneIndexConfig]
        with open(CONFIG_FILE, "r") as f:
            self._config = json.load(f)

    def get_config(self, index_url: str) -> Union[CraneIndexConfig, None]:
        "Get the config for a given index url. None in case the url is not registerd."
        return self._config.get(key=index_url, default=None)

    def set_config(self, index_url: str, config: CraneIndexConfig):
        self._config[index_url] = config
        self._write_config()

    def _write_config(self):
        "Save current state of the config to disk"
        with open(CONFIG_FILE, "w") as f:
            f.write(json.dumps(self._config))

###### Cache


class ExpiredTokens(Exception):
    "Error raised when expired tokens were attempted to get used."

    pass


class RequestError(Exception):
    "General request error"

    pass


class FailedRefreshRequest(RequestError):
    "Request to refresh tokens failed"

    pass


CACHE_DIR = os.path.join(Path.home(), ".cache", "crane", "python")
os.makedirs(CACHE_DIR, exists_ok=True)

TOKEN_CACHE_FILE = os.path.join(CACHE_DIR, "tokens.json")


class Tokens:
    "Token configs for a given index url"

    def __init__(
        self,
        access_token: str,
        access_token_exp_time: str,
        refresh_token: str,
        refresh_token_exp_time: str,
    ) -> None:
        pass
        self.access_token = access_token
        self.access_token_exp_time = datetime.datetime.fromtimestamp(
            access_token_exp_time
        )
        self.refresh_token = refresh_token
        self.refresh_token_exp_time = datetime.datetime.fromtimestamp(
            refresh_token_exp_time
        )

    def serialize_token_cache(self) -> Dict[str, str]:
        "Return dictionary to be stored in the json cache file"
        to_cache = {
            "access_token": self.access_token,
            "access_token_exp_time": self.access_token_exp_time.timestamp(),
            "refresh_token": self.refresh_token,
            "refresh_token_exp_time": self.refresh_token_exp_time.timestamp(),
        }
        return to_cache

    def access_token_expired(self):
        return self.access_token_exp_time < datetime.now()

    def refresh_token_expired(self):
        return self.refresh_token_exp_time < datetime.now()

    def expired_but_can_refresh(self):
        return self.access_token_exp_time() and not self.refresh_token_exp_time()

    def refresh_if_necessary(self, index_config: CraneIndexConfig):
        """Refresh tokens if necessary.

        That is, the access_token is expired but the refresh token is not.

        If the refresh token is also expired then an ExpiredTokens exeption is raised"""
        if self.expired_but_can_refresh():
            self.refresh(index_config=index_config)
        if self.refresh_token_expired():
            raise ExpiredTokens

    def refresh(self, index_config: CraneIndexConfig):
        """Refresh using refresh_token and the index config.

        An ExpiredTokens error is raised incase the refresh tokens was already expired."""

        if self.refresh_token_expired():
            raise ExpiredTokens

        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token,
            "client_id": index_config["client_id"]
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = urllib3.request(
            method="POST",
            url=index_config["token_url"],
            headers=headers,
            body=json.dumps(payload),
        )
        content = response.json()
        if response.status >= 400 or (not content) or not isinstance(content, dict):
            raise FailedRefreshRequest

        now = datetime.datetime.now()
        self.access_token = content["access_token"]
        self.refresh_token = content["refresh_token"]
        self.access_token_exp_time = now + datetime.timedelta(
            seconds=content["expires_in"]
        )
        self.refresh_token_exp_time = now + datetime.timedelta(
            seconds=content["refresh_expires_in"]
        )


class Cache:
    def __init__(self) -> None:
        # Key = index url
        self._cache: Dict[str, Tokens]
        with open(TOKEN_CACHE_FILE, "r") as f:
            self._cache = {url: Tokens(**tokens) for url, tokens in json.load(f)}

    def get_cached_token(self, index_url: str) -> Union[Tokens, None]:
        return self._cache.get(key=index_url, default=None)

    def set_cached_token(self, index_url: str, tokens: Tokens):
        self._cache[index_url] = Tokens
        self.write_cache()

    def write_cache(self):
        "Write current cache state back to disk"
        to_write = {
            url: tokens.serialize_token_cache() for url, tokens in self._cache.items()
        }
        with open(TOKEN_CACHE_FILE, "w") as f:
            f.write(json.dumps(to_write))

###### Authentication 

class FailedDeviceCodeRequest(RequestError):
    "Request for fetching device code failed"
    
    pass

class AuthorizationPendingFailed(RequestError):
    "An error occured when polling for the status."

        
def _perform_device_auth_flow(config: CraneIndexConfig) -> Tokens:
    """Perform device authentication for a given index config and return the tokens

    This is a blocking call that will only exist once the authentication by the user is performed.
    """

class UnregisterdIndex(Exception):
    
    pass


class Auth:
    "Authentication class for a given index_url"

    # Global config/cache for all configured indexes.
    config = CraneConfig()
    cache = Cache()

    def __init__(self, index_url: str) -> None:
        
        self.index_config = self.config.get_config(index_url)
        if not self.index_config:
            raise UnregisterdIndex(
                f"The index_url: {index_url} is not registed crane protected index."
            )
        self.tokens: Union[Tokens, None] = self.cache.get_cached_token(index_url)

    def authenticate(self) -> str:
        """Perform authentication flow (if necessary) and return the access_token.
        
        Authentication flow is only necessary when: no access_token was found, or was expired and 
        could also not get refreshed.
        """

        # Check if there is a cache to begin with.
        if self.tokens:
            try:
                return self.get_access_token()
            except ExpiredTokens:
                pass

        self._perform_device_auth_flow()
        self.cache.set_cached_token(self.tokens)


    def get_access_token(self) -> str:
        """Get access_token from cache or refresh token if possible.

        An ExpiredToken exeption is raised if both the access and refresh token are expired.
        """
        if not self.tokens.access_token_expired():
            return self.tokens.access_token 
        if self.tokens.expired_but_can_refresh():
            self.tokens.refresh(index_config=self.index_config)
            self.cache.write_cache()
            return self.tokens.access_token 
        raise ExpiredTokens

    def _perfom_device_auth_flow(self):
        """Perform device authentication flow.

        This is a blocking call that will only exist once the 
        authentication by the user is performed in the browser.
        """
        ## Part 1: request the device login.
        payload = {"client_id": self.config["client_id"], "scope": "openid offline_access"}

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = urllib3.request(
            method="POST",
            url=self.config["device_code_url"],
            headers=headers,
            body=json.dumps(payload),
        )
        content = response.json()
        if response.status >= 400 or (not content) or not isinstance(content, dict):
            raise FailedDeviceCodeRequest

        device_code = content["device_code"]
        if "interval" in content:
            request_interval = content["interval"]
        else:
            request_interval = 2


        ## Part 2: Call for user actions
        print("------------------------------")
        print("Please authenticate:")
        print(f"\tpoint your browser to: {content['verification_uri']}")
        print(f"\tand enter your user code: {content['user_code']}")
        if "verification_uri_complete" in content:
            print(f"\tor use the direct link: {content['verification_uri_complete']}")
        print("------------------------------" "")


        ## Part 3: Start polling:
        print("Waiting for authentication.", sep="", end="", flush=True)
        while True:
            time.sleep(request_interval)
            print(".", sep="", end="", flush=True)

            payload = {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": device_code,
                "client_id": self.config["client_id"]
            }

            headers = {"Content-Type": "application/x-www-form-urlencoded"}

            response = urllib3.request(
                method="POST",
                url=self.config["device_code_url"],
                headers=headers,
                body=json.dumps(payload),
            )
            content = response.json()
            if content is None:
                print(response)
                raise AuthorizationPendingFailed

            if "error" in content:
                if content["error"] == "authorization_pending":
                    continue
                else:
                    print(content)
                    raise AuthorizationPendingFailed

            now = datetime.datetime.now()

            self.tokens = Tokens(
                access_token = content["access_token"],
                refresh_token = content["refresh_token"],
                access_token_exp_time = now + datetime.timedelta(
                    seconds=content["expires_in"]
                ),
                refresh_token_exp_time = now + datetime.timedelta(
                    seconds=content["refresh_expires_in"]
                )
            )
