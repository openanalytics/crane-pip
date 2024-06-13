from typing import List
from subprocess import check_call, CalledProcessError
import logging
import sys

from .proxy import Address 

logger = logging.getLogger(__name__)

PIP_COMMANDS_WITH_INDEX = {'install', 'download', 'search', 'index', 'wheel'}

def requires_index(args: List[str]) -> bool:
    "Does the command in question requires the index?"
    if args and set(args).intersection(PIP_COMMANDS_WITH_INDEX):
        return True
    return False

def prepare_pip_args(args: List[str], proxy_address: Address) -> List[str]:
    """Prepare the argument list for the pip-subprocess call based on the rdepot-pip args
    
    Arguments:
    ----------
    args: List[str]
        Argument list as provided to rdepot-pip (exluding the rdepot-pip call itself)
        Eg. if the call was `rdepot-pip install pkg` then args = ['install', 'pkg']
    proxy_address: Address
        The address list on which the local proxy/index is exposed and we have to point to 
        subprocess pip call to.
    """
    if not requires_index(args):
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

def call_pip(args: List[str]= []) -> None:
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
        check_call(args = full_call)
    except CalledProcessError as e:
        logger.critical(f"pip crashed with an exit-code: {e.returncode}.")
        if e.stderr:
            logging.error(f"Stderror: {e.stderr.decode()}")
        raise RuntimePipError('pip process failed') from e
    except Exception as e:
        logger.critical(f"pip process failed to launch with the following error: {e}")
        raise LaunchPipError("Failed to launch pip") from e


