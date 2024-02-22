# -*- coding: utf-8 -*-
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
from .utils import testpath, classpath, chain, loghandler_members, modname
from .environ import TestEnviron
from .path import PathGuesser, PathFinder, RerunFile


logger = logging.getLogger(__name__)


class TestSuite(BaseTestSuite):
    """
    We override the suite so classes that begin with an underscore will be
    filtered out from running, this allows us to easily create base TestCase
    instances and not worry about them being run

    https://github.com/python/cpython/blob/3.7/Lib/unittest/suite.py
    """
    def addTest(self, test):
        """This will filter out "private" classes that begin with an underscore
        """
        add_it = True
        if isinstance(test, TestCase):
            add_it = not test.__class__.__name__.startswith("_")

        if add_it:
            super().addTest(test)

    def __str__(self):
        lines = []
        for test in self._tests:
            if isinstance(test, type(self)):
                lines.append(str(test))

            else:
                lines.append(testpath(test))

        return "\n".join(lines)

    def run(self, result, *args, **kwargs):
        # we surface any PathGuesser errors here because this is one of the
        # first times we have access to the result and we want PathGuesser's
        # errors itegrated with the rest of the error 
        if path_guesser := getattr(self, "path_guesser", None):
            for exc_info in path_guesser.get_any_error():
                self._createClassOrModuleLevelException(
                    result,
                    exc_info[1],
                    path_guesser.__class__.__name__,
                    self,
                    exc_info
                )

        return super().run(result, *args, **kwargs)


class TestLoader(BaseTestLoader):
    """This custom loader acts as the translation layer from the cli to our path
    guessing and finding classes

    https://docs.python.org/2/library/unittest.html#unittest.TestLoader
    https://github.com/python/cpython/blob/3.7/Lib/unittest/loader.py
    """
    suiteClass = TestSuite

    def loadTestsFromNames(self, names, *args, **kwargs):

        if names:
            ts = super().loadTestsFromNames(names, *args, **kwargs)

        else:
            ts = self.loadTestsFromName("", *args, **kwargs)

        ts.program = self.program

        test_count = ts.countTestCases()
        logger.debug("Found {} total tests".format(test_count))

        self.program.environ.update_env_for_test(test_count)

        return ts

    def loadTestsFromName(self, name, *args, **kwargs):
        ts = self.suiteClass()
        program = self.program
        environ = program.environ

        ts.program = program
        ts.path_guesser = pg = PathGuesser(
            name,
            basedir=self._top_level_dir,
            method_prefix=self.testMethodPrefix,
            prefixes=program.prefixes
        )
        found = False

        logger.debug("Searching for tests in directory: {}".format(pg.basedir))

        for i, pf in enumerate(pg.possible, 1):
            logger.debug("{}. Searching for tests matching: {}".format(i, pf))
            if pf.has_method():
                for c, mn in pf.method_names():
                    logger.debug(
                        'Found method test: {}'.format(testpath(c, mn))
                    )
                    found = True
                    ts.addTest(c(mn))
                    environ.counter["methods"] += 1

            elif pf.has_class():
                for c in pf.classes():
                    logger.debug('Found class test: {}'.format(classpath(c)))
                    found = True
                    ts.addTest(self.loadTestsFromTestCase(c))
                    environ.counter["classes"] += 1

            else:
                for m in pf.modules():
                    logger.debug('Found module test: {}'.format(m.__name__))
                    found = True
                    ts.addTest(self.loadTestsFromModule(m))
                    environ.counter["modules"] += 1

                # if we found a module that matched then don't try for method
                if found:
                    break

        return ts


class TestResult(BaseTestResult):
    """
    https://github.com/python/cpython/blob/3.7/Lib/unittest/result.py
    """
    def _show_status(self, status):
        if pyt_start := getattr(self, "_pyt_start", None):
            pyt_stop = time.time()
            self.stream.writeln(
                "{} ({}s)".format(
                    status,
                    round(pyt_stop - pyt_start, 2)
                )
            )

    def startTest(self, test):
        if self.showAll:
            self._pyt_start = time.time()
            self.stream.write("{}/{} ".format(
                self.testsRun + 1,
                self.program.environ.test_count,
            ))
            self.stream.flush()
        super().startTest(test)

    def addSuccess(self, test):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("ok")
            self.showAll = False
        super().addSuccess(test)
        self.showAll = orig_show_all

    def addError(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("ERROR")
        super().addError(test, err)
        self.showAll = orig_show_all

    def addFailure(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("FAIL")
        super().addFailure(test, err)
        self.showAll = orig_show_all

    def addExpectedFailure(self, test, err):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("expected failure")
        super().addExpectedFailure(test, err)
        self.showAll = orig_show_all

    def addUnexpectedSuccess(self, test):
        orig_show_all = self.showAll
        if self.showAll:
            self._show_status("unexpected success")
        super().addUnexpectedSuccess(test)
        self.showAll = orig_show_all

    def _setupStdout(self):
        super()._setupStdout()
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

        super()._restoreStdout()


class TestRunner(BaseTestRunner):
    """
    https://docs.python.org/3/library/unittest.html#unittest.TextTestRunner
    https://github.com/python/cpython/blob/3.7/Lib/unittest/runner.py
    """
    resultclass = TestResult

    def _makeResult(self):
        result = super()._makeResult()
        result.program = self.program
        return result

    def run(self, test):
        # this will be used to set the TestProgram instance into TestResult
        self.program = test.program

        result = super().run(test)

        if self.verbosity > 1:
            if len(result.errors) or len(result.failures):
                with RerunFile() as fp:
                    count = len(result.errors) + len(result.failures)
                    self.stream.writeln(
                        "Failed or errored {} tests:".format(count)
                    )
                    for testcase, failure in chain(result.errors, result.failures):
                        tp = testpath(testcase)
                        self.stream.writeln(tp)
                        fp.writeln(tp)
                self.stream.writeln("")

            if len(result.skipped):
                self.stream.writeln(
                    "Skipped {} tests:".format(len(result.skipped))
                )
                for testcase, failure in result.skipped:
                    self.stream.writeln(testpath(testcase))
                self.stream.writeln("")

        return result


class TestProgram(BaseTestProgram):
    """The main entrypoint into the module, this is where everything starts

    https://docs.python.org/3/library/unittest.html#unittest.main
    https://github.com/python/cpython/blob/3.7/Lib/unittest/main.py
    """
    @property
    def verbosity(self):
        return self._verbosity

    @verbosity.setter
    def verbosity(self, v):
        self._verbosity = v

        logger_name = modname()
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
        self.environ = TestEnviron()

        # according to the code, testLoader gets defaulted to
        # unittest.loader.defaultTestLoader which is an instance, so to override
        # it we should pass in our loader as an instance also
        testloader = TestLoader()
        # we want to keep open the possibility of grabbing values from this
        # later on down the line
        testloader.program = self

        kwargs.setdefault('testLoader', testloader)

        # according to the code testRunner is defaulted to a None and set to a
        # class in .runTests, where an instance is then created, so there are
        # no hooks to customize creation of it, it does pass .test into its
        # .run method though, so the hook will have to be there
        kwargs.setdefault('testRunner', TestRunner)

        # we want to get around all the .module is None checks
        kwargs.setdefault("module", __name__)

        # anything after this line will not be run because once we enter into
        # the parent's __init__ then it begins to actually compile and call all
        # the tests, it must call .runTests which can call sys.exit
        super().__init__(**kwargs)

    def createTests(self, from_discovery=False, Loader=None):
        """Ideally we would put a lot of this configuration in .parseArgs but
        that method calls this method or ._do_discovery
        """
        # if we didn't pass in any test names then we want to find all tests
        if not self.tests and self.rerun:
            self.testNames = list(RerunFile())

        # we need to set .testNames to anything but None to short circuit
        # parent's routing to try and load tests from a module
        if not self.testNames:
            self.testNames = []

        # if no prefixes were passed in through the CLI then we'll use any
        # environment defined prefixes
        if not getattr(self, "prefixes", None):
            self.prefixes = self.environ.get_prefixes()

        # TestLoader is used to load the tests and .test is set in parent's 
        # .createTest method
        super().createTests(
            from_discovery=False,
            Loader=Loader
        )

    def _getParentArgParser(self):
        """Get the argument parser and add any custom flags

        NOTE -- any flag you define will be set as an instance attribute
        on self because self is passed into the parser's .parse_args method as
        the Namespace object
        """
        from . import __version__ # avoid circular dependency

        parser = super()._getParentArgParser()

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

        parser.add_argument(
            '--prefix', "-P",
            dest="prefixes",
            action="append",
            default=[],
            #default=self.environ.get_prefixes(),
            help=(
                "The prefix(es)"
                " (python module paths where TestCase subclasses are found)"
            )
        )

        return parser


main = TestProgram

