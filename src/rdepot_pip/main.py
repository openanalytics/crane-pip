import logging
import sys

from .proxy import RDepotProxy
from .pip import call_pip, prepare_pip_args, requires_index

logger = logging.getLogger(__name__)

def main() -> int:
    # Remove first argument which is rdepot-pip
    args = sys.argv[1:]
    if requires_index(args):
        with RDepotProxy() as p:
            new_args = prepare_pip_args(args=args, proxy_address=p.proxy_address)
            call_pip(args = new_args)
    else: 
        call_pip(args = args)
    return 0
