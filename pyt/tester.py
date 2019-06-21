# -*- coding: utf-8 -*-
# https://docs.python.org/2/library/unittest.html
from __future__ import unicode_literals, division, print_function, absolute_import
import os
from unittest import (
    TestLoader as BaseTestLoader,
    TextTestRunner as BaseTestRunner,
    TextTestResult as BaseTestResult,
    TestSuite as BaseTestSuite,
    TestCase
)
from unittest.main import TestProgram as BaseTestProgram
import time
import logging
import argparse
import sys
import platform
import warnings

from .compat import *
from .utils import testpath, classpath, chain, loghandler_members
from .environ import TestEnviron
from .path import PathGuesser, PathFinder, RerunFile


logger = logging.getLogger(__name__)


class TestSuite(BaseTestSuite):
    """
    We override the suite so classes that begin with an underscore will be filtered
    out from running, this allows us to easily create base TestCase instances and
    not worry about them being run

    https://github.com/python/cpython/blob/3.7/Lib/unittest/suite.py
    """
    def addTest(self, test):
        """This will filter out "private" classes that begin with an underscore"""
        add_it = True
        if isinstance(test, TestCase):
            add_it = not test.__class__.__name__.startswith("_")

        if add_it:
            super(TestSuite, self).addTest(test)

    def __str__(self):
        lines = []
        for test in self._tests:
            if isinstance(test, type(self)):
                lines.append(str(test))
            else:
                lines.append(testpath(test))

        return "\n".join(lines)


class TestLoader(BaseTestLoader):
    """
    This custom loader acts as the translation layer from the cli to our path
    guessing and finding classes

    https://docs.python.org/2/library/unittest.html#unittest.TestLoader
    https://github.com/python/cpython/blob/3.7/Lib/unittest/loader.py
    https://github.com/python/cpython/blob/2.7/Lib/unittest/loader.py
    """
    suiteClass = TestSuite

    def loadTestsFromName(self, name, *args, **kwargs):
        ts = self.suiteClass()
        environ = TestEnviron.get_instance()
        ti = PathGuesser(
            name,
            basedir=self._top_level_dir,
            method_prefix=self.testMethodPrefix
        )
        found = False
        logger.debug("Searching for tests in directory: {}".format(ti.basedir))
        for i, tc in enumerate(ti.possible, 1):
            logger.debug("{}. Searching for tests matching: {}".format(i, tc))
            if tc.has_method():
                for c, mn in tc.method_names():
                    logger.debug('Found method test: {}'.format(testpath(c, mn)))
                    found = True
                    ts.addTest(c(mn))
                    environ.counter["methods"] += 1

            elif tc.has_class():
                for c in tc.classes():
                    logger.debug('Found class test: {}'.format(classpath(c)))
                    found = True
                    ts.addTest(self.loadTestsFromTestCase(c))
                    environ.counter["classes"] += 1

            else:
                for m in tc.modules():
                    logger.debug('Found module test: {}'.format(m.__name__))
                    found = True
                    ts.addTest(self.loadTestsFromModule(m))
                    environ.counter["modules"] += 1

                # if we found a module that matched then don't try for method
                if found: break

        if not found:
            ti.raise_any_error()

        logger.debug("Found {} total tests".format(ts.countTestCases()))
        return ts

    def loadTestsFromNames(self, names, *args, **kwargs):
        ts = self.suiteClass()
        for name in names:
            name_suite = self.loadTestsFromName(name, *args, **kwargs)
            ts.addTest(name_suite)

        return ts


class TestResult(BaseTestResult):
    """
    https://github.com/python/cpython/blob/3.7/Lib/unittest/result.py
    https://github.com/python/cpython/blob/3.7/Lib/unittest/runner.py
    """
    total_tests = 0

    def _show_status(self, status):
        pyt_start = self._pyt_start
        pyt_stop = time.time()
        self.stream.writeln("{} ({}s)".format(status, round(pyt_stop - pyt_start, 2)))

    def startTest(self, test):
        if self.showAll:
            self._pyt_start = time.time()
            self.stream.write("{}/{} ".format(
                self.testsRun + 1,
                self.total_tests,
            ))
            self.stream.flush()
        super(TestResult, self).startTest(test)

    def addSuccess(self, test):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("ok")
            self.showAll = False
        super(TestResult, self).addSuccess(test)
        self.showAll = orig_show_all

    def addError(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("ERROR")
        super(TestResult, self).addError(test, err)
        self.showAll = orig_show_all

    def addFailure(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("FAIL")
        super(TestResult, self).addFailure(test, err)
        self.showAll = orig_show_all

    def addExpectedFailure(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("expected failure")
        super(TestResult, self).addExpectedFailure(test, err)
        self.showAll = orig_show_all

    def addUnexpectedSuccess(self, test):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("unexpected success")
        super(TextTestResult, self).addUnexpectedSuccess(test)
        self.showAll = orig_show_all

    def _setupStdout(self):
        super(TestResult, self)._setupStdout()
        if self.buffer:
            # Now I realize why I had all that custom stdout/stderr handling
            # code in the previous version, turns out by default buffer didn't
            # remove logs when logging had already been messed with, so now I
            # mess with the loggers and buffer them
            for r in loghandler_members():
                ohs = [
                    (self._original_stdout, self._stdout_buffer),
                    (self._original_stderr, self._stderr_buffer)
                ]
                for oh in ohs:
                    if r.member is oh[0]:
                        setattr(r.handler, r.member_name, oh[1])

    def _restoreStdout(self):
        if self.buffer:
            for r in loghandler_members():
                ohs = [
                    (self._original_stdout, self._stdout_buffer),
                    (self._original_stderr, self._stderr_buffer)
                ]
                for oh in ohs:
                    if r.member is oh[1]:
                        setattr(r.handler, r.member_name, oh[0])

        super(TestResult, self)._restoreStdout()


class TestRunner(BaseTestRunner):
    """
    https://docs.python.org/3/library/unittest.html#unittest.TextTestRunner
    https://github.com/python/cpython/blob/3.7/Lib/unittest/runner.py
    """
    resultclass = TestResult

    def _makeResult(self):
        instance = super(TestRunner, self)._makeResult()
        instance.total_tests = self.running_test.countTestCases()

        environ = TestEnviron.get_instance()
        environ.update_env_for_test(instance.total_tests)

        return instance

    def run(self, test):
        if is_py2:
            w = test.main.warnings
            if w:
                warnings.filterwarnings("error")

        self.running_test = test
        result = super(TestRunner, self).run(test)
        self.running_test = None

        if self.verbosity > 1:
            if len(result.errors) or len(result.failures):
                with RerunFile() as fp:
                    count = len(result.errors) + len(result.failures)
                    self.stream.writeln("Failed or errored {} tests:".format(count))
                    for testcase, failure in chain(result.errors, result.failures):
                        tp = testpath(testcase)
                        self.stream.writeln(tp)
                        fp.writeln(tp)
                self.stream.writeln("")

            if len(result.skipped):
                self.stream.writeln("Skipped {} tests:".format(len(result.skipped)))
                for testcase, failure in result.skipped:
                    self.stream.writeln(testpath(testcase))
                self.stream.writeln("")

        return result


class TestProgram(BaseTestProgram):
    """
    https://docs.python.org/3/library/unittest.html#unittest.main
    https://docs.python.org/2.7/library/unittest.html#unittest.main
    https://github.com/python/cpython/blob/3.7/Lib/unittest/main.py
    https://github.com/python/cpython/blob/2.7/Lib/unittest/main.py
    """
    @property
    def verbosity(self):
        return self._verbosity

    @verbosity.setter
    def verbosity(self, v):
        self._verbosity = v

        logger_name = __name__.split(".")[0]
        logger = logging.getLogger(logger_name)
        if len(logger.handlers) == 0:
            log_handler = logging.StreamHandler(stream=sys.stderr)
            log_formatter = logging.Formatter('[%(levelname).1s] %(message)s')
            log_handler.setFormatter(log_formatter)
            logger.addHandler(log_handler)

        if v < 2:
            logger.setLevel(logging.WARNING)
        else:
            logger.setLevel(logging.DEBUG)

    def __init__(self, **kwargs):
        kwargs.setdefault('testLoader', TestLoader())
        kwargs.setdefault('testRunner', TestRunner)
        super(TestProgram, self).__init__(**kwargs)

    def parseArgs(self, argv):
        #pout.v(argv)
        if is_py2:
            if len(argv) > 1 and argv[1].lower() == 'discover':
                self._do_discovery(argv[2:])
            else:
                parser = self._getParentArgParser()
                parser.parse_args(argv[1:], self)
                self.createTests()

        else:
            ret = super(TestProgram, self).parseArgs(argv)

        # after parent's parseArgs is ran self.testNames should be set and
        # should contain all the passed in patterns pyt can use to find the
        # tests, but parseArgs() also calls createTests() which uses that
        # information so by the time we get to right here all tests have been
        # created
        #pout.v(self.testNames, self)

    def createTests(self, *args, **kwargs):
        # if we didn't pass in any test names then we want to find all tests
        test_names = getattr(self, "testNames", [])
        if len(test_names) == 1 and not test_names[0]:
            if self.rerun:
                self.testNames = list(RerunFile())

        super(TestProgram, self).createTests(*args, **kwargs)

        # we want to keep open the possibility of grabbing values from this
        # later on down the line
        self.test.main = self

    def _print_help(self):
        if is_py2:
            try:
                self.usageExit()
            except SystemExit:
                pass

        else:
            super(TestProgram, self)._print_help()

    def _getMainArgParser(self, parent):
        parser = super(TestProgram, self)._getMainArgParser(parent)

        # python3 will trigger discovery if no tests are passed in, so we
        # override that functionality so we get routed to our path guesser
        for action in parser._actions:
            if action.dest == "tests":
                action.default = [""]
        #pout.v(parser._positionals)
        return parser

    def _getParentArgParser(self):
        from . import __version__ # avoid circular dependency

        if is_py2:
            # so python 2.7 unittest uses optparse, which makes it so you can't
            # specify flags in any position, so we basically are going to build
            # a shadow argparser and bypass 2.7's opt parser so we can be a bit
            # more flexible
            parser = argparse.ArgumentParser()
            parser.prog = self.progName
            parser.print_help = self._print_help
            parser.add_argument(
                '-v', '--verbose',
                dest='verbosity',
                action='store_const',
                const=2,
                help='Verbose output'
            )
            parser.add_argument(
                '-q', '--quiet',
                dest='verbosity',
                action='store_const',
                const=0,
                help='Quiet output'
            )
            parser.add_argument(
                '-f', '--failfast',
                dest='failfast',
                action='store_true',
                help='Stop on first fail or error'
            )
            parser.add_argument(
                '-c', '--catch',
                dest='catchbreak',
                action='store_true',
                help='Catch Ctrl-C and display results so far'
            )
            parser.add_argument(
                '-b', '--buffer',
                dest='buffer',
                action='store_true',
                help='Buffer stdout and stderr during tests'
            )
            parser.add_argument(
                'testNames',
                metavar='tests',
                default=[""],
                #dest='testNames',
                nargs='*',
                help='a list of any number of test modules, classes and test methods.'
            )

        else:
            parser = super(TestProgram, self)._getParentArgParser()

        parser.add_argument(
            "--version", "-V",
            action='version',
            version="%(prog)s {}, Python {} ({})".format(
                __version__,
                platform.python_version(),
                sys.executable
            )
        )

        # https://docs.python.org/2/library/warnings.html
        parser.add_argument(
            '--warnings', "--warning", "-w", "-W",
            dest='warnings',
            action='store_const',
            const="error",
            default="",
            help='Converts warnings into errors'
        )

        parser.add_argument(
            '--debug', '-d',
            dest='verbosity',
            action='store_const',
            const=2,
            help='Verbose output'
        )

        parser.add_argument(
            '--rerun',
            action='store_true',
            help='Rerun previously failed tests'
        )

        return parser


main = TestProgram

