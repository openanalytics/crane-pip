# Second attempt
from datetime import datetime, timedelta
import json
import time
from .config import CraneServerConfig, crane_configs
from .cache import CraneTokens, token_cache

import urllib3


class ExpiredTokens(Exception):
    "Error raised when expired tokens were attempted to get used."

    pass

class UnregisterdIndex(Exception):
    "Error raised when index config information is required but not present"

    pass

class NoTokenCache(Exception):
    "Error raised when cache info is required but not present"

    pass


class RequestError(Exception):
    "General request error"

    pass


class FailedRefreshRequest(RequestError):
    "Request to refresh tokens failed"

    pass


class FailedDeviceCodeRequest(RequestError):
    "Request for fetching device code failed"

    pass


class AuthorizationPendingFailed(RequestError):
    "An error occured when polling for the status."

    pass


def refresh(tokens: CraneTokens, index_config: CraneServerConfig) -> CraneTokens:
    """Fetch new tokens using the refresh token and return a **new copy** of tokens.

    An ExpiredTokens error is raised incase the refresh tokens was already expired."""

    if tokens.refresh_token_expired():
        raise ExpiredTokens

    payload = {
        "grant_type": "refresh_token",
        "refresh_token": tokens.refresh_token,
        "client_id": index_config.client_id,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = urllib3.request(
        method="POST",
        url=index_config.token_url,
        headers=headers,
        body=json.dumps(payload),
    )
    content = response.json()
    if response.status >= 400 or (not content) or not isinstance(content, dict):
        raise FailedRefreshRequest

    now = datetime.now()
    new_tokens = CraneTokens(
        access_token = content["access_token"],
        refresh_token = content["refresh_token"],
        access_token_exp_time = now + timedelta(seconds=content["expires_in"]),
        refresh_token_exp_time = now + timedelta(seconds=content["refresh_expires_in"])
    )
    return new_tokens

def perform_device_auth_flow(index_url: str) -> CraneTokens:
    """Perform device authentication for a given index config and return the acquired tokens.

    The calling is blocking until the user has performed the authentication in a browser.
    """

    index_config = crane_configs.get(index_url)
    if not index_config:
        raise UnregisterdIndex(
            "Cannot perform device authentication flow for unregisted index {index_url}. "
            "Use the `register-index` command to register the index."
        )

    ## Part 1: request the device login.
    payload = {"client_id": index_config.client_id, "scope": "openid offline_access"}

    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = urllib3.request(
        method="POST",
        url=index_config.device_code_url,
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
            "client_id": index_config.client_id,
        }

        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        response = urllib3.request(
            method="POST",
            url=index_config.device_code_url,
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

        now = datetime.now()

        CraneTokens(
            access_token=content["access_token"],
            refresh_token=content["refresh_token"],
            access_token_exp_time=now + timedelta(seconds=content["expires_in"]),
            refresh_token_exp_time=now
            + timedelta(seconds=content["refresh_expires_in"]),
        )


def get_access_token(index_url: str) -> str:
    """Get access_token from cache or if possible request new ones using the cached refesh tokens.

    Exceptions:
    -----------
    NoTokenCache:
        In case no tokens were cached for the index url, which this function assumes to be 
        present.
    ExpiredTokens:
        Tokens are present but both access and refresh token are already epxired.
    UnregisterdIndex:
        Incase there are no configurations found for the index url which are needed if we want 
        to request new tokens using the refresh token.
    """
    tokens = token_cache[index_url]
    index_config = crane_configs[index_url]

    if not crane_configs:
        raise UnregisterdIndex("Index url = {index_url} is not registed. "
            "Please registed the index first using the 'regerist-index' command.")

    if not tokens:
        raise NoTokenCache(
            f"No authentication tokens are cached for {index_url}."
            " Please authenticate first using the authenticate function."
        )

    if not tokens.access_token_expired():
        return tokens.access_token
    if tokens.expired_but_can_refresh():
        new_tokens = refresh(tokens, index_config)
        token_cache[index_url] = refresh(tokens, index_config)
        return new_tokens.access_token
    raise ExpiredTokens

def authenticate(index_url: str) -> str:
    """Authenticate with the device flow if necessary and return the access token.

    Preferable the token is first checked if present in the cache or if it can get refreshed.
    """

    token = token_cache.get(index_url)
    if not token or token.is_expired():
        new_tokens = perform_device_auth_flow(index_url)
        token_cache[index_url] = new_tokens
        return new_tokens.access_token

    return get_access_token(index_url)
