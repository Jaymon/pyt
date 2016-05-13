#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import argparse
import os

from pyt import tester, __version__


def console():
    '''
    cli hook

    return -- integer -- the exit code
    '''
    parser = argparse.ArgumentParser(description='Easy Python Testing')
    parser.add_argument('names', metavar='NAME', nargs='*', default=[], help='the test(s) you want to run')
    parser.add_argument('--basedir', dest='basedir', default=os.curdir, help='base directory, defaults to current working directory')
    parser.add_argument('--debug', dest='debug', action='store_true', help='print debugging info')
    parser.add_argument("--version", "-V", action='version', version="%(prog)s {}".format(__version__))
    parser.add_argument('--all', dest='run_all', action='store_true', help='run all tests if no NAME specified')
    #parser.add_argument('--fad', dest='daf', action='store_true', help='run with --all --no-faifast --debug')

    # https://docs.python.org/2/library/unittest.html#command-line-options
    #parser.add_argument('--no-failfast', dest='no_failfast', action='store_true', help='turns off fail fast')
    #parser.add_argument('--no-buffer', dest='no_buffer', action='store_true', help='turns off buffer when more than one test is ran')
    parser.add_argument('--buffer', dest='buffer', action='store_true', help='Buffer stdout and stderr during test runs')

    args, test_args = parser.parse_known_args()

    test_args.insert(0, sys.argv[0])
    ret_code = 0

    if args.run_all:
        args.names = ['']
        args.buffer = True

    # create the singleton
    environ = tester.TestEnviron.get_instance(args)

    if not args.names:
        args.names.append('')

    if args.names:
        for name in args.names:
            ret_code |= tester.run_test(
                name,
                args.basedir,
                argv=test_args,
            )

    else:
        environ.unbuffer()
        # http://unix.stackexchange.com/a/8815/118750
        parser.print_help()
        ret_code = 1

    sys.exit(ret_code)


if __name__ == "__main__":
    # allow both imports of this module, for entry_points, and also running this module using python -m pyt
    console()

