from enum import Enum
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
from threading import Thread
from typing import NamedTuple, Tuple, Dict, Union

import urllib3
import logging 

logger = logging.getLogger(__name__)

class ProxyError(Exception):
    pass 

class ProxyControlError(ProxyError):
    pass

class Address(NamedTuple):
    "Address of the proxy"
    host: str 
    port: int

    def url(self) -> str:
        return f"http://{self.host}:{self.port}"

class Index(NamedTuple):
    "Represent index with an optional bearer token to use in communication"
    url: str 
    token: Union[str, None] = None

class RDepotProxy:
    """A proxy that acts as a index to clients that want to interact with the rdepot index.

    On initialization, the user is requested to authenticate against the configured rdepot url(s), 
    if not cached already.

    The proxy can be started/stopped using the start/stopped and can be checked if running via 
    the is_running property. The life time of the proxy can also be managed via a context manager.
    """
    def __init__(self, rdepot_url = Union[str, None]) -> None:
        self._proxy : ThreadedHTTPServer
        self._proxy_thread : Thread

        self.proxy_address = Address(host = '127.0.0.1', port = 9999)
        self.is_running:bool = False

        # TODO Read config to get order of rdepot urls
        rdepot_url = rdepot_url

        # TODO authenticate for the provided rdepot_urls
        token = ""
    
        # Indexes which the proxy server will forward requests to.
        # TODO determine if this is public knowledge or not?
        self._indexes: Tuple[Index] = (
            #Index(url = rdepot_url, token = token),
            Index(url="https://pypi.python.org/simple"), # PyPI fallback
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
            raise ProxyControlError(f"No proxy is running to stop.")

    def __exit__(self, *exc):
        try:
            self.stop()
        except ProxyControlError:
            logger.debug("Proxy already stopped in the context manager.")


class Method(Enum):
    "Supported proxy methods"
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
    headers: Dict[str,str]
    content: Union[bytes, None]

class ProxyHTTPRequestHandler(BaseHTTPRequestHandler):

    # Indexes to use in communication. This property is set on RDepotProxy initialization.
    indexes: Tuple[Index]

    protocol_version = "HTTP/1.1"

    def _handle_request(self, method: Method) -> ResponseClient:
        """Businuess logic for handeling the request."""

        headers = dict(self.headers)

        # TODO implement fall back logic based on the different urls:
        index = self.indexes[0]

        # TODO not exactly sure what the correct Host should be... but for now seems we can leave 
        # it out. TODO investigate
        del headers["Host"]
        if index.token:
            headers['Authorization'] = 'Bearer ' + index.token

        resp = urllib3.request(
            method.value,
            url = index.url + self.path,
            decode_content = False,
            headers = headers
        )
        return ResponseClient(
            status_code=resp.status,
            headers=dict(resp.headers),
            content=resp.data
        )

    def do_request(self):
        "Top-level Wrapper for handeling all the different kind of method requests"
        try:
            if self.command not in SUPPORTED_METHODS:
                self.send_response(405)
                self.send_header('Content-Length', "0")
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
            self.send_error(502, 'Bad gateway')

# Dispatch all the different method calls to do_request
for m in ('HEAD', 'GET', 'OPTIONS', 'POST', 'PUT', 'DELETE', 'PATCH'):
    setattr(ProxyHTTPRequestHandler, 'do_' + m, ProxyHTTPRequestHandler.do_request)

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

    def handle_error(self, request, client_address):
        # ignore ConnectionResetError
        if sys.exc_info()[0] is not ConnectionResetError:
            super().handle_error(request, client_address)

if __name__=='main':
    proxy = RDepotProxy()
    proxy.start()
