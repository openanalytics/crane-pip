from enum import Enum
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread
from typing import NamedTuple, Tuple, Dict, Union

import urllib3
import logging

from .auth import Auth

logger = logging.getLogger(__name__)


class ProxyError(Exception):
    "General proxy error"

    pass


class ProxyControlError(ProxyError):
    "Error during the lifetime managment of the proxy."

    pass


class ProxyAddress(NamedTuple):
    "Address of the proxy"

    host: str
    port: int

    def url(self) -> str:
        return f"http://{self.host}:{self.port}"


class IndexConfig(NamedTuple):
    "Index configuration."

    url: str
    auth_token: Union[str, None] = None


class IndexProxy:
    """A proxy acting as an index that adds the required auth headers for a crane protected index.

    Configuration:
    --------------
    The index to which the proxy forwards is specified in the construction. If a given package is
    not found the index the request is forwarded to PyPI.

    (Configuration is in active development)

    Authenticate:
    -------------
    On initialization, if not cached, the user is requested to authenticate in a browser. This lets
    the server act on the users behave against the crane server.

    Note, if the provided index url is not a registered crane protected index no authentication
    flow is then initialized.

    Lifetime:
    ---------
    Start and stop the server using the methods start/stop. The lifetime can also be managed via
    a context manager.
    """

    def __init__(self, index_url=str) -> None:
        self._proxy: ThreadedHTTPServer
        self._proxy_thread: Thread

        self.proxy_address = ProxyAddress(host="127.0.0.1", port=9999)
        self.is_running: bool = False

        # TODO authenticate for the provided index_urls
        auth = Auth()
        token = auth.authenticate()

        # Indexes which the proxy server will forward requests to.
        # TODO determine if this is public knowledge or not?
        self._indexes: Tuple[IndexConfig] = (
            IndexConfig(url=index_url, auth_token=token),
            IndexConfig(url="https://pypi.python.org/simple"),  # PyPI fallback
        )

        # Provide configured url/token info to handler class that each request instance would need.
        ProxyHTTPRequestHandler.indexes = self._indexes

    def start(self) -> None:
        "Start up the proxy an seperate thread."
        if not self.is_running:
            self._proxy = ThreadedHTTPServer(self.proxy_address, ProxyHTTPRequestHandler)
            print(f"Starting proxy on {self.proxy_address.url()}")
            self._proxy_thread = Thread(target=self._proxy.serve_forever)
            self._proxy_thread.start()
            self.is_running = True
        else:
            raise ProxyControlError(f"Proxy is already running on {self.proxy_address}")

    def __enter__(self):
        self.start()
        return self

    def stop(self):
        "Shut down the proxy."
        if self.is_running:
            logger.info("Shutting down proxy server")
            self._proxy.shutdown()
            self.is_running = False
        else:
            raise ProxyControlError(f"No proxy running to stop.")

    def __exit__(self, *exc):
        try:
            self.stop()
        except ProxyControlError:
            logger.debug("Proxy already stopped in the context manager.")


class Method(Enum):
    "Supported http methods of proxy index."

    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    GET = "GET"

    def response_has_content(self) -> bool:
        if self == Method.HEAD:
            return False
        else:
            return True


SUPPORTED_METHODS = [m.value for m in Method]


class ResponseClient(NamedTuple):
    "Http response to send back to the client (pip, ...)"

    status_code: int
    headers: Dict[str, str]
    content: Union[bytes, None]


class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):
    # Indexes to use in communication. This property is set on IndexProxy initialization.
    indexes: Tuple[IndexConfig]
    protocol_version = "HTTP/1.1"

    def _handle_request(self, method: Method) -> ResponseClient:
        """Businuess logic for handeling the request."""

        headers = dict(self.headers)

        # TODO implement fall back logic based on the different urls:
        index = self.indexes[0]

        # TODO not exactly sure what the correct Host should be... but for now seems we can leave
        # it out. TODO investigate
        del headers["Host"]
        if index.auth_token:
            headers["Authorization"] = "Bearer " + index.auth_token

        resp = urllib3.request(
            method.value,
            url=index.url + self.path,
            decode_content=False,
            headers=headers,
        )
        return ResponseClient(
            status_code=resp.status, headers=dict(resp.headers), content=resp.data
        )

    def do_request(self):
        "Top-level Wrapper for handeling all the different kind of method requests"
        try:
            if self.command not in SUPPORTED_METHODS:
                self.send_response(405)
                self.send_header("Content-Length", "0")
                self.end_headers()
                return

            method = Method(self.command)
            resp = self._handle_request(method)
            self.send_response(resp.status_code)
            for key, value in resp.headers.items():
                self.send_header(key, value)
            self.end_headers()
            if method.response_has_content() and resp.content:
                self.wfile.write(resp.content)

        except Exception:
            self.send_error(502, "Bad gateway")


# Dispatch all the different method calls to do_request
for m in ("HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"):
    setattr(ProxyHTTPRequestHandler, "do_" + m, ProxyHTTPRequestHandler.do_request)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # ignore ConnectionResetError
        if sys.exc_info()[0] is not ConnectionResetError:
            super().handle_error(request, client_address)


if __name__ == "main":
    proxy = IndexProxy()
    proxy.start()
