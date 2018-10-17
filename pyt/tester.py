# -*- coding: utf-8 -*-
# https://docs.python.org/2/library/unittest.html
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import unittest
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

from .compat import *
from .utils import testpath, classpath, chain
from .environ import TestEnviron
from .path import PathGuesser, PathFinder


logger = logging.getLogger(__name__)


# https://hg.python.org/cpython/file/tip/Lib/unittest/suite.py
class TestSuite(BaseTestSuite):
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


# https://hg.python.org/cpython/file/648dcafa7e5f/Lib/unittest/loader.py
class TestLoader(BaseTestLoader):
    """
    https://docs.python.org/2/library/unittest.html#unittest.TestLoader
    """
    suiteClass = TestSuite

    def loadTestsFromName(self, name, *args, **kwargs):
        ts = self.suiteClass()
        environ = TestEnviron.get_instance()
        ti = PathGuesser(name, environ.basedir, self.testMethodPrefix)
        found = False
        logger.debug("Searching for tests in directory: {}".format(environ.basedir))
        for i, tc in enumerate(ti.possible, 1):
            logger.debug("{}. Searching for tests matching:".format(i))
            logger.debug("    {}".format(tc))
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


# https://hg.python.org/cpython/file/648dcafa7e5f/Lib/unittest/runner.py#l28
class TestResult(BaseTestResult):
    """
    This is overridden so I can keep original copies of stdout and stderr, and also
    so I can have control over the stringIO instances that would be used if buffer is
    passed in. What was happening previously was our custom test loader would load
    all the testing modules before unittest had a chance to buffer them, so they would
    have real references to stdout/stderr and would still print out all the logging.
    """
    total_tests = 0

#     def __init__(self, stream=None, descriptions=None, verbosity=None):
#         pout.v(verbosity)
#         super(TestResult, self).__init__(stream, descriptions, verbosity)

#     def startTest(self, test):
#         """ran once before each TestCase"""
#         self._pyt_start = time.time()
# 
#         logger.debug("{}/{} - Starting {}".format(
#             self.testsRun + 1,
#             self.total_tests,
#             testpath(test)
#         ))
#         super(TestResult, self).startTest(test)

#     def stopTest(self, test):
#         """ran once after each TestCase"""
#         super(TestResult, self).stopTest(test)
# 
#         pyt_start = self._pyt_start
#         del(self._pyt_start)
# 
#         pyt_stop = time.time()
# 
#         logger.debug("Stopping {} after {}s".format(
#             testpath(test),
#             round(pyt_stop - pyt_start, 2)
#         ))

    def show_status(self, status):
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

#     def stopTest(self, test):
#         pout.t()
#         if self.showAll:
#             pyt_start = self._pyt_start
#             pyt_stop = time.time()
#             self.stream.write(" ({}s) ".format(round(pyt_stop - pyt_start, 2)))
#             self.stream.flush()

    def addSuccess(self, test):
        orig_show_all = self.showAll
        if self.showAll:
            self.show_status("ok")
            self.showAll = False
        super(TestResult, self).addSuccess(test)
        self.showAll = orig_show_all

    def addError(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self.show_status("ERROR")
        super(TestResult, self).addError(test, err)
        self.showAll = orig_show_all

    def addFailure(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self.show_status("FAIL")
        super(TestResult, self).addFailure(test, err)
        self.showAll = orig_show_all

    def addExpectedFailure(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self.show_status("expected failure")
        super(TestResult, self).addExpectedFailure(test, err)
        self.showAll = orig_show_all

    def addUnexpectedSuccess(self, test):
        orig_show_all = self.showAll
        if self.showAll:
            self.show_status("unexpected success")
        super(TextTestResult, self).addUnexpectedSuccess(test)
        self.showAll = orig_show_all

#     def __init__(self, *args, **kwargs):
#         super(TestResult, self).__init__(*args, **kwargs)
#         self._original_stdout = TestEnviron.stdout_stream
#         self._original_stderr = TestEnviron.stderr_stream
#         self._stdout_buffer = TestEnviron.stdout_buffer
#         self._stderr_buffer = TestEnviron.stderr_buffer


class TestRunner(BaseTestRunner):
    """
    This sets our custom result class and also makes sure the stream that gets passed
    to the runner is the correct stderr stream and not a buffered stream, so it can
    still print out the test information even though it buffers everything else, just
    like how it is done with the original unittest

    https://docs.python.org/3/library/unittest.html#unittest.TextTestRunner
    https://hg.python.org/cpython/file/648dcafa7e5f/Lib/unittest/runner.py
    """
    resultclass = TestResult

    def __init__(self, *args, **kwargs):
        self.environ = TestEnviron.get_instance()
        if self.environ.warnings:
            if is_py2:
                warnings.filterwarnings("error")
            else:
                # Changed in version 3.2: Added the warnings argument
                kwargs["warnings"] = "error"
        #stream = self.environ.stderr_stream
        super(TestRunner, self).__init__(
            *args,
            **kwargs
        )

    def _makeResult(self):
        instance = super(TestRunner, self)._makeResult()
        instance.total_tests = self.running_test.countTestCases()
        self.environ.update_env_for_test(instance.total_tests)
        return instance

    def run(self, test):
        self.running_test = test
        result = super(TestRunner, self).run(test)
        self.running_test = None

        if self.verbosity > 1:
            if len(result.errors) or len(result.failures):
                self.stream.writeln("Test failures/errors:")
                for testcase, failure in chain(result.errors, result.failures):
                    self.stream.writeln(testpath(testcase))

            if len(result.skipped):
                self.stream.writeln("Tests skipped:")
                for testcase, failure in result.skipped:
                    self.stream.writeln(testpath(testcase))

        return result



class TestProgram(BaseTestProgram):
    """
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
        tl = TestLoader()
        kwargs.setdefault('testLoader', tl)
        kwargs.setdefault('testRunner', TestRunner)
        super(TestProgram, self).__init__(**kwargs)

    def parseArgs(self, argv):
        #pout.v(argv)
        if is_py2:
            parser = self._getParentArgParser()
            parser.parse_known_args()

        ret = super(TestProgram, self).parseArgs(argv)

#         if self.verbosity > 1:
#             logger_name = __name__.split(".")[0]
#             logger.setLevel(logging.DEBUG)
#             logger2 = logging.getLogger(logger_name)
#             #logger = logging.getLogger()
#             pout.v(logger2, logger.parent)
#             logger2.setLevel(logging.DEBUG)

        # after parent's parseArgs is ran self.testNames should be set and
        # should contain all the passed in patterns pyt can use to find the
        # tests
        #pout.v(self.testNames)

    def _getParentArgParser(self):
        from . import __version__ # avoid circular dependency

        if is_py2:
            parser = argparse.ArgumentParser()

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

        return parser


main = TestProgram

# def main2(name="", basedir="", **kwargs):
#     '''
#     run the test found with find_test() with unittest
# 
#     **kwargs -- dict -- all other args to pass to unittest
#     '''
#     ret_code = 0
# 
# 
#     # create the environment
#     buf = kwargs.pop("buffer", False)
#     warnings = kwargs.pop("warnings", False)
#     environ = TestEnviron.get_instance(
#         buffer=buf,
#         warnings=warnings
#     )
# 
#     tl = TestLoader(basedir, environ)
# 
#     #kwargs.setdefault('argv', [__name__.split(".")[0]])
#     #kwargs['argv'] = kwargs['argv'] + [name]
#     kwargs["argv"] = None
#     kwargs["defaultTest"] = name
# 
#     kwargs.setdefault('exit', False)
#     kwargs.setdefault('testLoader', tl)
#     kwargs.setdefault('testRunner', TestRunner)
#     #kwargs.setdefault('testRunner', tr)
# 
#     # https://docs.python.org/2/library/unittest.html#unittest.main
#     try:
#         ret = unittest.main(**kwargs)
#         if len(ret.result.errors) or len(ret.result.failures):
#             ret_code = 1
# 
#             # TODO: can we print skipped tests?
#             logger.debug("Test failures/errors:")
#             for testcase, failure in chain(ret.result.errors, ret.result.failures):
#                 logger.debug(testpath(testcase))
# 
#         elif not ret.result.testsRun:
#             ret_code = 1
# 
#         logger.debug('Test returned: {}'.format(ret_code))
# 
#     finally:
#         environ.unbuffer()
# 
#     return ret_code


