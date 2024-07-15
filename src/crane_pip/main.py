from importlib import import_module
from .argparser import root_parser

# Load the different commando's module to have their arg parser get attached to the root_parser.
import_module(".cmd_pip")
import_module(".cmd_serve")
import_module(".cmd_register")

def main() -> int:
    parsed_args = root_parser.parse_args()
    return parsed_args.entrypoint_command(parsed_args)
