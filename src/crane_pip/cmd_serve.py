from .argparser import subparser
from .proxy import IndexProxy

server_parser = subparser.add_parser(
    "serve",
    help="Serve a local index proxy performing authentication for the crane protected index.",
    description="The serve command launches a local index proxy that third party clients like (pip, uv, poetry, ...) can use to communicate with the crane protected index server. \n\nLaunching the proxy will require an interactive login (if index url is not cached). The proxy will forward request to the specified crane index url and add the correct authentication set."
)

server_parser.add_argument('url', "Index url to forward the requests to. Note, the url should have already been registered by the 'crane index register' command.")
server_parser.add_argument('--port', '-p', 'port to serve the proxy under.', default=9999)

def entrypoint_serve(args):
    proxy = IndexProxy(index_url=args.url, port = args.port)
    print(f"Serving index proxy on: {proxy.proxy_address.url()}")
    proxy.start_here()
    return 0


server_parser.set_defaults(entrypoint_command=entrypoint_serve)
