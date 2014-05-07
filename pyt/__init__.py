# -*- coding: utf-8 -*-
import argparse
import re
import os
import ast
import unittest
from unittest import TestCase # to allow from pyt import TestCase, Assert
import sys
import inspect

from assertion import Assert
from . import tester
from . import echo


__version__ = '0.6.9'

def console():
    '''
    cli hook

    return -- integer -- the exit code
    '''
    parser = argparse.ArgumentParser(description='Easy Python Testing')
    parser.add_argument('names', metavar='NAME', nargs='+', default=[''], help='the test(s) you want to run')
    parser.add_argument('--basedir', dest='basedir', default=os.curdir, help='base directory, defaults to current working directory')
    parser.add_argument('--debug', dest='debug', action='store_true', help='print debugging info')
    parser.add_argument("-v", "--version", action='version', version="%(prog)s {}".format(__version__))

    # https://docs.python.org/2/library/unittest.html#command-line-options
    parser.add_argument('--not-failfast', dest='not_failfast', action='store_true', help='turns off fail fast')
    parser.add_argument('--not-buffer', dest='not_buffer', action='store_true', help='turns off buffer')

    args, test_args = parser.parse_known_args()

    echo.DEBUG = args.debug

    test_args.insert(0, sys.argv[0])
    ret_code = 0

    for name in args.names:
        ret_code |= tester.run_test(
            name,
            args.basedir,
            argv=test_args,
            failfast=args.not_failfast,
            buffer=args.not_buffer,
        )

    return ret_code

