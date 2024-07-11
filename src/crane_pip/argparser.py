import argparse

root_parser = argparse.ArgumentParser(allow_abbrev=False)
subparser = root_parser.add_subparsers(required=True, dest='commando')

# Subparsers for indiviual commands are added in their respective module: '.cmd_{command_name}'
