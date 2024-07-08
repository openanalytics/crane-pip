import logging
import sys

from .proxy import IndexProxy
from .pip import call_pip, prepare_pip_args, requires_index, get_index_url

logger = logging.getLogger(__name__)


def main() -> int:
    # Remove first argument which is
    args = sys.argv[1:]
    url = get_index_url(args)
    if requires_index(args):
        with IndexProxy(index_url=url) as p:
            new_args = prepare_pip_args(args=args, proxy_address=p.proxy_address)
            call_pip(args=new_args)
    else:
        call_pip(args=args)
    return 0
