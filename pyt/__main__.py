#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import platform
import argparse
import os

from pyt import tester, __version__, main


def console():
    '''
    cli hook

    return -- integer -- the exit code
    '''
    parser = argparse.ArgumentParser(description='Easy Python Testing')
    parser.add_argument('names', metavar='NAME', nargs='*', default=[], help='the test(s) you want to run')
    parser.add_argument('--basedir', dest='basedir', default=os.curdir, help='run from this directory')
    parser.add_argument(
        "--version", "-V",
        action='version',
        version="%(prog)s {}, Python {} ({})".format(
            __version__,
            platform.python_version(),
            sys.executable
        )
    )
    parser.add_argument(
        '--all', "-a",
        dest='run_ball',
        action='store_true',
        help='run all tests with buffer'
    )
    parser.add_argument(
        '--debug', "-d",
        dest='debug',
        action='store_true',
        help='print debugging info'
    )
    parser.add_argument(
        '--buffer', "-b",
        dest='buffer',
        action='store_true',
        help='Buffer stdout and stderr during test runs'
    )
    parser.add_argument(
        '--failfast', "-f",
        dest='failfast',
        action='store_true',
        help='Stop running tests on first encountered failure'
    )
    parser.add_argument(
        '--warnings', "--warning", "-w", "-W",
        dest='warnings',
        action='store_true',
        help='Converts warnings into errors'
    )

    args, test_args = parser.parse_known_args()

    # ripped from unittest.__main__.py
    if sys.argv[0].endswith("__main__.py"):
        sys.argv[0] = "python -m pyt"

    # https://docs.python.org/2/library/unittest.html#command-line-options
    test_args.insert(0, sys.argv[0])
    if args.failfast:
        test_args.append("--failfast")
    ret_code = 0

    if args.run_ball:
        args.names = ['']
        args.buffer = True

    ret_code = main(
        args.names,
        args.basedir,
        argv=test_args,
        buffer=args.buffer,
        warnings=args.warnings,
#         verbosity
#         args=args
    )

#     else:
#         environ.unbuffer()
#         # http://unix.stackexchange.com/a/8815/118750
#         parser.print_help()
#         ret_code = 1

    sys.exit(ret_code)


if __name__ == "__main__":
    # allow both imports of this module, for entry_points, and also running this module using python -m pyt
    console()

