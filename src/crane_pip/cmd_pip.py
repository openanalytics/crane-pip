from typing import List, Union
from subprocess import check_call, CalledProcessError
import logging
import sys

from .argparser import subparser
from .proxy import ProxyAddress, IndexProxy

logger = logging.getLogger(__name__)

# Parser for the crane pip command (not to be confused with the pip command itself)
argparser_pip = subparser.add_parser("pip", help='Any pip command, but crane indexes do get correctly authenticated.', add_help=False)

class NoIndexError(Exception):
    pass

def entrypoint_pip(args_for_pip) -> int:
    "Entry point of the 'crane pip' command."

    # Arguments not explicitly parsed are meant for pip.
    if not call_requires_index(args_for_pip):
        call_pip(args=args_for_pip)
        return 0

    url = get_index_url(args_for_pip)
    with IndexProxy(index_url=url) as p:
        new_args = prepare_pip_args(args=args_for_pip, proxy_address=p.proxy_address)
        call_pip(args=new_args)

    return 0

argparser_pip.set_defaults(entrypoint_pip=entrypoint_pip)


PIP_COMMANDS_WITH_INDEX = {"install", "download", "search", "index", "wheel"}


def get_index_url(args: List[str]) -> Union[str, None]:
    "Get the index url from a pip command call."
    is_url = False
    for arg in args:
        if is_url:
            return arg
        if arg == "-i" or arg == "--index-url":
            is_url = True
    return None


def call_requires_index(args: List[str]) -> bool:
    "Does the pip call in question require the index?"
    if args and set(args).intersection(PIP_COMMANDS_WITH_INDEX):
        return True
    return False


def prepare_pip_args(args: List[str], proxy_address: ProxyAddress) -> List[str]:
    """Prepare the argument list for the pip-subprocess call based on the crane pip args

    Arguments:
    ----------
    args: List[str]
        Argument list of the the pip command portion. Eg. the list of arguments one would issue
        to a normal `pip {args}` command (without the `pip` portion then).
    proxy_address: Address
        The address list on which the local proxy/index is exposed and we have to point to
        subprocess pip call to.
    """
    if not call_requires_index(args):
        return args

    # Filter out --index and --extra-index specification
    filtered_args = []
    skip = False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg == "--index-url" or arg == "-i" or arg == "--extra-index-url":
            skip = True
            continue
        filtered_args.append(arg)

    # Point pip towards the local proxy
    resulting_args = filtered_args + ["-i", proxy_address.url()]
    return resulting_args


class NoExecutableError(Exception):
    pass


class PipError(Exception):
    pass


class RuntimePipError(PipError):
    pass


class LaunchPipError(PipError):
    pass


def call_pip(args: List[str] = []) -> None:
    """Call pip in a sub-process with the list of arguments specified.

    Arguments:
    ----------
    args: list[str]
        A list of arguments to call pip with. Note, the 'pip' command itself does not need to
        be specified.

        Eg. to install a pkg the argument list looks like: ['install', 'pkg']

    Returns:
    --------
    None:
        Currently None, indicating the the call was a success. This might change in the future.

    Exceptions:
    -----------
    NoExecutableError:
        No python executable was found to launch pip with.
    RuntimePipError:
        Pip stopped with a non-zero exit-code.
    LaunchPipError:
        Pip could not get launched.
    """

    exec = sys.executable
    if not exec:
        raise NoExecutableError("Could not find any python executable")

    logger.info(f"Using executable to call pip: {exec}")

    try:
        full_call = [exec, "-m", "pip"] + args
        check_call(args=full_call)
    except CalledProcessError as e:
        logger.critical(f"pip crashed with an exit-code: {e.returncode}.")
        if e.stderr:
            logging.error(f"Stderror: {e.stderr.decode()}")
        raise RuntimePipError("pip process failed") from e
    except Exception as e:
        logger.critical(f"pip process failed to launch with the following error: {e}")
        raise LaunchPipError("Failed to launch pip") from e



