# Second attempt
from datetime import datetime, timedelta
import time
import logging
from typing import Dict
import webbrowser
from urllib.parse import urlencode
from .config import ServerConfig, server_configs
from .cache import CraneTokens, token_cache

logger = logging.getLogger(__name__)
import urllib3


class ExpiredTokens(Exception):
    "Error raised when expired tokens were attempted to get used."

    pass


class UnregisterdServer(Exception):
    "Error raised when the config of unregistered crane server is requested but not present"

    pass


class NoTokenCache(Exception):
    "Error raised when cache info is required but not present"

    pass


class RequestError(Exception):
    "General request error"

    pass


class FailedDeviceCodeRequest(RequestError):
    pass


class FailedTokenRequest(RequestError):
    "Request to refresh tokens failed"

    def __init__(self, msg: str, auth_pending: bool = False) -> None:
        self.auth_pending = auth_pending
        super().__init__(msg)


class AuthorizationPendingFailed(RequestError):
    "An error occured when polling for the status."

    pass


def _fetch_token(grant_type: str, grant_key: str, crane_config: ServerConfig) -> CraneTokens:
    """Fetch tokens based on the specified grant_type.

    Arguments:
    ----------
    grant_type: "refresh_token" | "device_code"
        Which grant type are we performing?
    grant_key: str
        Refresh tokens incase grant_type == "refresh_token". Else the device_code.
    crane_config: ServerConfig
        Configs

    Response:
    ---------
    CraneTokens
        Tokens.

    Exceptions:
    -----------
    FailedRefreshRequest:
        Incase the fetching failed and grant_type = "refresh_token".
    AuthorizationPendingFailed:
        Incase the fetching failed and grant_type = "device_code".
    """

    payload = {
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        "client_id": crane_config.client_id,
    }
    if grant_type == "refresh_token":
        payload.update(
            {
                "grant_type": "refresh_token",
                "refresh_token": grant_key,
            }
        )
    elif grant_type == "device_code":
        payload.update(
            {
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
                "device_code": grant_key,
            }
        )
    else:
        raise TypeError(f"Unknonw grant_type: {grant_type}.")

    payload = urlencode(payload)
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = urllib3.request(
        method="POST",
        url=crane_config.token_url,
        headers=headers,
        body=payload,
    )

    try:
        content = response.json()
        if not isinstance(content, dict):
            raise TypeError("Response is not a json object")
    except Exception as e:
        raise FailedTokenRequest(f"Unsupported response format from token_url: {e}")

    if "error" in content:
        if content["error"] == "authorization_pending":
            raise FailedTokenRequest("Authorization not complete yet", auth_pending=True)
        if "error_description" in content:
            raise AuthorizationPendingFailed(
                f"Authorization failed. Reason: {content['error_description']}"
            )

    now = datetime.now()
    if content["refresh_expires_in"] == 0:
        refresh_token_exp_time = None
    else:
        refresh_token_exp_time = now + timedelta(seconds=content["refresh_expires_in"])

    return CraneTokens(
        access_token=content["access_token"],
        refresh_token=content["refresh_token"],
        access_token_exp_time=now + timedelta(seconds=content["expires_in"]),
        refresh_token_exp_time=refresh_token_exp_time,
    )


def refresh(tokens: CraneTokens, crane_config: ServerConfig) -> CraneTokens:
    """Fetch new tokens using the refresh token and return a **new copy** of tokens.

    An ExpiredTokens error is raised incase the refresh tokens was already expired."""

    if tokens.refresh_token_expired():
        raise ExpiredTokens
    return _fetch_token(
        grant_type="refresh_token", grant_key=tokens.refresh_token, crane_config=crane_config
    )


def _request_device_code(crane_config) -> Dict:
    """Request a device code login. Reponsd with the content of the response."""

    ## Part 1: request the device code
    payload = urlencode({"client_id": crane_config.client_id, "scope": "openid offline_access"})
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = urllib3.request(
        method="POST", url=crane_config.device_url, body=payload, headers=headers
    )

    # breakpoint()
    try:
        content = response.json()
        if not isinstance(content, dict):
            raise TypeError("Response is not json object")
    except Exception as e:
        raise FailedDeviceCodeRequest(f"Unexpected response from device_code_url: {e}")

    if response.status >= 400:
        if "error_description" in content:
            raise FailedDeviceCodeRequest(
                f"Failed to request device code. Reason: {content['error_description']}"
            )
        raise FailedDeviceCodeRequest(f"Failed to request device code. Response: {content}")

    return content


def perform_device_auth_flow(crane_url: str) -> CraneTokens:
    """Perform device authentication for a given crane server and return the acquired tokens.

    The calling is blocking until the user has performed the authentication in a browser.
    """

    crane_config = server_configs.get(crane_url)
    if not crane_config:
        raise UnregisterdServer(
            f"Cannot perform device authentication flow for unregistered index {crane_url}. "
            "Please first register the index using the 'crane index register' command."
        )

    # Part 1 request device code

    content = _request_device_code(crane_config)
    if "interval" in content:
        request_interval = content["interval"]
    else:
        request_interval = 2

    ## Part 2: Call for user actions
    try:
        webbrowser.open(content["verification_uri_complete"], new=2)
        print("------------------------------")
        print("Please authenticate in the webbrowser page that just opened or")
    except Exception:
        print("------------------------------")
        print("Please authenticate:")

    print(f"point your browser to: {content['verification_uri']}")
    print(f"and enter your user code: {content['user_code']}")
    if "verification_uri_complete" in content:
        print(f"or use the direct link: {content['verification_uri_complete']}")
    print("------------------------------" "")

    ## Part 3: Start polling:
    print("Waiting for authentication.", sep="", end="", flush=True)
    timeout = timedelta(minutes=10)
    start = datetime.now()
    while True:
        if datetime.now() > (start + timeout):
            raise AuthorizationPendingFailed("Timeout: user did not completed the authentication.")

        time.sleep(request_interval)
        print(".", sep="", end="", flush=True)

        try:
            tokens = _fetch_token(
                grant_type="device_code",
                grant_key=content["device_code"],
                crane_config=crane_config,
            )
        except FailedTokenRequest as e:
            if e.auth_pending:
                continue
            raise AuthorizationPendingFailed("Fetching token failed") from e
        print("Authentication successful!")
        return tokens


def get_access_token(crane_url: str) -> str:
    """Get access_token from cache or if possible request new ones using the cached refesh tokens.

    Exceptions:
    -----------
    NoTokenCache:
        In case no tokens were cached for the url, which this function assumes to be present.
    ExpiredTokens:
        Tokens are present but both access and refresh token are already epxired.
    UnregisterdServer:
        Incase there are no configurations found for the url which are needed if we want
        to request new tokens using the refresh token.
    """
    tokens = token_cache[crane_url]
    crane_config = server_configs[crane_url]

    if not server_configs:
        raise UnregisterdServer(
            "url = {crane_url} is not registed. "
            "Please registed the crane server 'register' command."
        )

    if not tokens:
        raise NoTokenCache(
            f"No authentication tokens are cached for {crane_url}."
            " Please authenticate first using the authenticate function."
        )

    if not tokens.access_token_expired():
        return tokens.access_token
    if tokens.expired_but_can_refresh():
        new_tokens = refresh(tokens, crane_config)
        token_cache[crane_url] = new_tokens
        return new_tokens.access_token
    raise ExpiredTokens


def authenticate(crane_url: str) -> str:
    """Authenticate with the device flow if necessary and return the access token.

    Preferable the token is first checked if present in the cache or if it can get refreshed.
    """

    token = token_cache.get(crane_url)
    if not token or token.is_expired():
        new_tokens = perform_device_auth_flow(crane_url)
        token_cache[crane_url] = new_tokens
        return new_tokens.access_token

    return get_access_token(crane_url)
