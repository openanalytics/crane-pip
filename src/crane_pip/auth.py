# Second attempt
from datetime import datetime, timedelta
import time
import logging
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


class FailedRefreshRequest(RequestError):
    "Request to refresh tokens failed"

    pass


class FailedDeviceCodeRequest(RequestError):
    "Request for fetching device code failed"

    pass


class AuthorizationPendingFailed(RequestError):
    "An error occured when polling for the status."

    pass


def refresh(tokens: CraneTokens, crane_config: ServerConfig) -> CraneTokens:
    """Fetch new tokens using the refresh token and return a **new copy** of tokens.

    An ExpiredTokens error is raised incase the refresh tokens was already expired."""

    if tokens.refresh_token_expired():
        raise ExpiredTokens

    logger.info("Refreshing access tokes.")
    payload = urlencode({
        "grant_type": "refresh_token",
        "refresh_token": tokens.refresh_token,
        "client_id": crane_config.client_id,
    })
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    response = urllib3.request(
        method="POST",
        url=crane_config.token_url,
        headers=headers,
        body=payload,
    )
    content = response.json()
    if response.status >= 400 or (not content) or not isinstance(content, dict):
        raise FailedRefreshRequest

    now = datetime.now()
    if content['refresh_expires_in']==0:
        refresh_token_exp_time = None
    else:
        refresh_token_exp_time = now + timedelta(seconds=content["refresh_expires_in"])

    new_tokens = CraneTokens(
        access_token = content["access_token"],
        refresh_token = content["refresh_token"],
        access_token_exp_time = now + timedelta(seconds=content["expires_in"]),
        refresh_token_exp_time = refresh_token_exp_time
    )
    return new_tokens


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

    ## Part 1: request the device code
    payload = urlencode({"client_id": crane_config.client_id, "scope": "openid offline_access"})
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = urllib3.request(
        method="POST",
        url=crane_config.device_url,
        body = payload,
        headers=headers
    )
    
    # breakpoint()
    content = response.json()
    if response.status >= 400 or (not content) or not isinstance(content, dict):
        raise FailedDeviceCodeRequest

    device_code = content["device_code"]
    if "interval" in content:
        request_interval = content["interval"]
    else:
        request_interval = 2

    ## Part 2: Call for user actions
    try: 
        webbrowser.open(content['verification_uri_complete'], new = 2)
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
    while True:
        time.sleep(request_interval)
        print(".", sep="", end="", flush=True)

        payload = urlencode({
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            "device_code": device_code,
            "client_id": crane_config.client_id,
        })

        headers = {"Content-Type": "application/x-www-form-urlencoded"}


        response = urllib3.request(
            method="POST",
            url=crane_config.token_url,
            headers=headers,
            body=payload,
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

        print("\nAuthentication successfull!")
        now = datetime.now()
        if content['refresh_expires_in']==0:
            refresh_token_exp_time = None
        else:
            refresh_token_exp_time = now + timedelta(seconds=content["refresh_expires_in"])

        return CraneTokens(
            access_token=content["access_token"],
            refresh_token=content["refresh_token"],
            access_token_exp_time=now + timedelta(seconds=content["expires_in"]),
            refresh_token_exp_time = refresh_token_exp_time
        )


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
        raise UnregisterdServer("url = {crane_url} is not registed. "
            "Please registed the crane server 'register' command.")

    if not tokens:
        raise NoTokenCache(
            f"No authentication tokens are cached for {crane_url}."
            " Please authenticate first using the authenticate function."
        )

    if not tokens.access_token_expired():
        logger.info("Using cached access token")
        return tokens.access_token
    if tokens.expired_but_can_refresh():
        new_tokens = refresh(tokens, crane_config)
        token_cache[crane_url] = refresh(tokens, crane_config)
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
