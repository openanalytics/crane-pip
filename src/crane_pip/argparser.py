import argparse

root_parser = argparse.ArgumentParser(allow_abbrev=False)
subparser = root_parser.add_subparsers(title = 'commands', dest='command')

def entrypoint_crane(args) -> int:
    root_parser.print_help()
    return 0

root_parser.set_defaults(entrypoint_command = entrypoint_crane)

# Subparsers for indiviual commands are added in their respective module: '.cmd_{command_name}'
