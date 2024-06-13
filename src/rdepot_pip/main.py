import logging
import sys
from typing import List, Union

from .proxy import RDepotProxy
from .pip import call_pip, prepare_pip_args, requires_index

logger = logging.getLogger(__name__)

def get_index_url(args: List[str]) -> Union[str, None]:
    "Get the index url specified via -i or --index-url." 
    is_url = False
    for arg in args:
        if is_url:
            return arg
        if arg == "-i" or arg == "--index-url":
            is_url = True
    return None

def main() -> int:
    # Remove first argument which is rdepot-pip
    args = sys.argv[1:]
    url = get_index_url(args) 
    if requires_index(args):
        with RDepotProxy(rdepot_url=url) as p:
            new_args = prepare_pip_args(args=args, proxy_address=p.proxy_address)
            call_pip(args = new_args)
    else: 
        call_pip(args = args)
    return 0
