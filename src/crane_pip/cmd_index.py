import sys
from difflib import get_close_matches
from .argparser import subparser
from .config import ServerConfig, server_configs

### 'crane index'
# Parser for the crane pip command (not to be confused with the pip command itself)
index_parser = subparser.add_parser(
    "index",
    help='Manage registered crane-indexes.',
    description="Manage the registered crane protected indexes."
)

def entrypoint_index(args) -> int:
    index_parser.print_help()
    return 0

index_parser.set_defaults(entrypoint_command=entrypoint_index)

### 'crane index register'

# Add another level of sub commands.
subsubparser = index_parser.add_subparsers(title = 'subcommands', dest='index_command')

# Todo check with other on description authentication arguments
register_parser = subsubparser.add_parser(
    "register",
    help='Register or update crane-index settings',
    description='Register a private package index that is protected by a crane server. '
        'Authentication settings of the crane server are to be provided. See arguments below. '
        'If the index url in question was already registered, then the settings are updated.'
)

register_parser.add_argument('url', help = 'index-url of the private package index that is protected by a crane server.')
register_parser.add_argument('client-id', help = 'Client-id that the crane client should use.')
register_parser.add_argument('token-url', help = 'Url to request access/refresh tokens from.')
register_parser.add_argument('device-url', help = 'Url to request the device code from.')

def entrypoint_register(args) -> int:
    "Entry point of the 'crane register' command"
    
    # TODO maybe add some argument checking... Like is the url actually a resource protected by 
    # a crane server.

    # Positional arguments containing a `-` can only be accessed through the internal dict.
    ns = args.__dict__
    server_configs[args.url] = ServerConfig(
        client_id=ns['client-id'],
        token_url=ns['token-url'],
        device_url=ns['device-url']
    )

    return 0

register_parser.set_defaults(entrypoint_command=entrypoint_register)

### 'crane index list'

# Todo check with other on description.
list_parser = subsubparser.add_parser(
    "list",
    help='List all the registered crane indexes with their settings.',
)

list_parser.add_argument('--url', '-u', nargs='*', help= 'Set of urls to for which only the settings should be returned.')

def entrypoint_list(args) -> int:
    template = """{url}
    client-id: {client_id}
    token-url: {token_url} 
    device-url: {device_url}"""
    
    urls = list(server_configs.keys())
    if args.url:
        urls = [u for u in urls if u in args.url]
    
    for u in urls:
        filled_in_template = template.format(
            url=u,
            client_id=server_configs[u].client_id,
            token_url=server_configs[u].token_url,
            device_url=server_configs[u].device_url,
        )
        print(filled_in_template)
    return 0

list_parser.set_defaults(entrypoint_command=entrypoint_list)


### 'crane index remove'
remove_parser = subsubparser.add_parser(
    "remove",
    help='Remove a registered crane index.',
)

remove_parser.add_argument('url', help = 'Index url to remove from the registered list of crane indexes.')

def entrypoint_remove(args) -> int:
    try: 
        del server_configs[args.url]
    except KeyError:
        sys.stderr.write(f'Index not found: "{args.url}"\n')
        known_indexes = list(server_configs.keys())
        close_match = get_close_matches(
            word=args.url,
            possibilities=known_indexes,
            n=1
        )
        if close_match:
            sys.stderr.write(f'Did you mean: "{close_match[0]}"?\n')
        return 1
    return 0

remove_parser.set_defaults(entrypoint_command=entrypoint_remove)
