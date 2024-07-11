from importlib import import_module
from .argparser import root_parser

# Load the different commando's module to have their arg parser get attached to the root_parser.
import_module(".cmd_pip")

def main() -> int:
    parsed_args, unknown_args = root_parser.parse_known_args()
    return parsed_args.entrypoint_command(parsed_args, unknown_args)
