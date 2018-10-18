#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
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

    if is_py2:
        from unittest.main import USAGE_AS_MAIN
        main.USAGE = USAGE_AS_MAIN

    main(module=None)


if __name__ == "__main__":
    # allow both imports of this module, for entry_points, and also running this module using python -m pyt
    console()

