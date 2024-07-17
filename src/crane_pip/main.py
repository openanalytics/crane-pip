from importlib import import_module

from .argparser import root_parser

# Load the different commando's module to have their arg parser get attached to the root_parser.
import_module(".cmd_pip", "crane_pip")
import_module(".cmd_serve", "crane_pip")
import_module(".cmd_index", "crane_pip")

def main() -> int:
    args, unknown_args = root_parser.parse_known_args()
    if args.command == 'pip':
        exit_code = args.entrypoint_pip(args_for_pip = unknown_args)
    else:
        exit_code = args.entrypoint_command(args)
    return exit_code
