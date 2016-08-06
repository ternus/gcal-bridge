
from __future__ import print_function

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)
