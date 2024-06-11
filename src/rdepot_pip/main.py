import logging
from typing import List
import sys
from subprocess import check_call, CalledProcessError

logger = logging.getLogger(__name__)

def authenticate(index: List = []) -> None:
    """Authenticate the user against the provided index."""
    
    # Look up cached token. 

    # If available, use refresh token to regenerate the OAuth 2 token. 

    # Else, acquire token with interactive setting.

    logger.info("TODO Authenticated")


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


def main() -> int:

    # logging 
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Read index configs:
    
    authenticate()
    
    # With local_index as i: (context manager)


    # Remove first argument which is rdepot-pip
    args = sys.argv[1:]

        # Relace --index with local spinned up
        # Remove --extra-index
        # Remove and store --proxy 
    
        # Call pip internally

    call_pip(args = args)

    return 0
