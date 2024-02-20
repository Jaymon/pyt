#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import platform
import argparse
import os

from pyt import tester, __version__, main
from pyt.compat import *


def console():
    # ripped from unittest.__main__.py
    if sys.argv[0].endswith("__main__.py"):
        executable = os.path.basename(sys.executable)
        sys.argv[0] = executable + " -m pyt"

    main(module=None)


if __name__ == "__main__":
    # allow both imports of this module, for entry_points, and also running this
    # module using python -m pyt
    console()

