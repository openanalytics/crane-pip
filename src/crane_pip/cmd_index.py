from .argparser import subparser
from .config import ServerConfig, server_configs

### 'crane index'
# Parser for the crane pip command (not to be confused with the pip command itself)
index_parser = subparser.add_parser(
    "index",
    help='Manage registered crane-indexes.',
    description="Manage the registred crane protected indexes. "
        "Calling '%(prog) index' with no arguments simply lists the current registered url's.",
)

def entrypoint_index(args) -> int:
    for index in server_configs.keys():
        print(index)
    return 0

index_parser.set_defaults(entrypoint_command=entrypoint_index)

### 'crane index register'

# Add another level of sub commands.
subsubparser = index_parser.add_subparsers(dest='index_command')

# Todo check with other on description authentication arguments
register_parser = subsubparser.add_parser(
    "register",
    help='Register or update crane-index settings',
    description='Register a new crane protected index by specifying the crane server url and its '
        'authentication settings. In particular the client id that the crane client should use.\n'
        'If the index url in question was already registered update the settings.'
)

register_parser.add_argument('url', 'Url of the crane protected index.')
register_parser.add_argument('client-id', 'OAuth client id.')
register_parser.add_argument('token-url', 'Token url of the identity provider used by the crane server.')
register_parser.add_argument('device-code-url', 'Device code url of the identity provider used by the crane server')

def entrypoint_register(args) -> int:
    "Entry point of the 'crane register' command"
     
    server_configs[args.url] = ServerConfig(
        client_id=args.client_id,
        token_url=args.token_url,
        device_code_url=args.device_code_url
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
    template = """
{url} :
    client-id: {client_id}
    token-url: {token_url} 
    device-code-url: {device_code_url}"""
    
    urls = list(server_configs.keys())
    if args.url:
        urls = [u for u in urls if u in args.url]
    
    for u in urls:
        filled_in_template = template.format(
            url=u,
            client_id=server_configs[u].client_id,
            token_url=server_configs[u].token_url,
            device_code_url=server_configs[u].device_code_url,
        )
        print(filled_in_template)
    return 0

list_parser.set_defaults(entrypoint_command=entrypoint_list)


### 'crane index remove'
remove_parser = subsubparser.add_parser(
    "remove",
    help='Remove a registered crane index.',
)

remove_parser.add_argument('url', 'Index url to remove from the registered list of crane indexes.')

def entrypoint_remove(args) -> int:
    try: 
        del server_configs[args.url]
    except KeyError:
        pass
    return 0

remove_parser.set_defaults(entrypoint_command=entrypoint_remove)
