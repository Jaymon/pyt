import os
from collections.abc import Generator
from unittest import (
    TestLoader,
    TextTestRunner,
    TextTestResult,
    TestSuite,
    TestCase,
)
from unittest.main import TestProgram, _convert_names
import time
import logging
import argparse
import sys
import platform
import warnings
import itertools
import inspect
import re

from .compat import *
from .utils import testpath, classpath, loghandler_members, modname
from .environ import TestEnviron
from .path import PathGuesser, PathFinder, RerunFile


logger = logging.getLogger(__name__)


class TestSuite(TestSuite):
    """
    https://github.com/python/cpython/blob/3.7/Lib/unittest/suite.py
    """
    def get_method_names(self, depth=0, indent="\t"):
        """Get all the test method names this suite represents in a
        hierarchical listing

        :param depth: int, how much `indent` should be applied
        :param indent: str, the indentation characters, (indent * depth will
            be the prefix placed on each line
        :returns: str, the method names
        """
        lines = []
        has_method_names = False

        if name := getattr(self, "name", ""):
            lines.append((indent * depth) + name)
            depth += 1

        for test in self._tests:
            if isinstance(test, TestSuite):
                if line := test.get_method_names(depth, indent):
                    lines.append(line)
                    has_method_names = True

            else:
                if line := testpath(test):
                    lines.append((indent * depth) + line)
                    has_method_names = True

        return "\n".join(lines) if has_method_names else ""

    def get_testcases(self) -> Generator[TestCase]:
        """Get all the test cases this testsuite represents"""
        for test in self._tests:
            if isinstance(test, TestSuite):
                yield from test.get_testcases()

            elif isinstance(test, TestCase):
                yield test

            else:
                logger.warning("Unknown test type: %s", type(test))

    def get_testpaths(self) -> Generator[str]:
        """Get the full test paths (<MODULE>.<CLASSNAME>.<METHOD_NAME>)
        for all the tests this testsuite represents"""
        for tc in self.get_testcases():
            if tp := testpath(tc):
                yield tp

    def run(self, result, *args, **kwargs):
        # we surface any PathGuesser errors here because this is one of the
        # first times we have access to the result and we want PathGuesser's
        # errors integrated with the rest of the error 
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


class TestLoader(TestLoader):
    """This custom loader acts as the translation layer from the cli to our
    path guessing and finding classes

    https://docs.python.org/3/library/unittest.html#unittest.TestLoader
    https://github.com/python/cpython/blob/3.7/Lib/unittest/loader.py
    """
    suiteClass = TestSuite

    def loadTestsFromNames(self, names, *args, **kwargs):
        test = super().loadTestsFromNames(names, *args, **kwargs)
        test.program = self.program

        test_count = test.countTestCases()
        logger.debug("Found {} total tests".format(test_count))

        self.program.environ.update_env_for_test(test_count)

        return test

    def loadTestsFromName(self, name, *args, **kwargs):
        test = self.suiteClass()
        program = self.program
        environ = program.environ

        test.program = program
        test.path_guesser = PathGuesser(
            name,
            basedir=self._top_level_dir,
            method_prefix=self.testMethodPrefix,
            prefixes=program.prefixes,
        )

        logger.debug(
            f"Searching for tests in directory: {test.path_guesser.basedir}"
        )

        for i, pf in enumerate(test.path_guesser.possible, 1):
            logger.debug("{}. Searching for tests matching {}".format(i, pf))
            if pf.has_method():
                for c, mn in pf.method_names():
                    logger.debug(
                        'Found method test: {}'.format(testpath(c, mn))
                    )
                    suite = self.loadTestsFromMethodName(c, mn)
                    suite.name = f"{c.__module__}.{c.__qualname__}"
                    test.addTest(suite)
                    environ.counter["methods"] += 1

            elif pf.has_class():
                for c in pf.classes():
                    logger.debug('Found class test: {}'.format(classpath(c)))
                    suite = self.loadTestsFromTestCase(c)
                    suite.name = f"{c.__module__}.{c.__qualname__}"
                    test.addTest(suite)
                    environ.counter["classes"] += 1

            else:
                found = False

                for m in pf.modules():
                    logger.debug('Found module test: {}'.format(m.__name__))
                    found = True
                    suite = self.loadTestsFromModule(m)
                    suite.name = m.__name__
                    test.addTest(suite)
                    environ.counter["modules"] += 1

                # if we found a module that matched then don't try for method
                if found:
                    break

        return test

    def loadTestsFromMethodName(self, testCaseClass, method_name):
        testCaseNames = self.getTestCaseNames(testCaseClass, [method_name])
        suite = self.suiteClass(map(testCaseClass, testCaseNames)) 
        return suite

    def getTestCaseNames(
        self,
        testCaseClass: type[TestCase],
        testnames: list[str]|None = None,
    ) -> list[str]:
        """Get all the test case test methods

        This extends parent's functionality by allowing `testnames` to be
        passed in. See `.loadTestFromMethodName` to see why this was added

        This filters found testnames through any defined ignore patterns

        This will filter `testCaseClass` names that start with an underscore
        because this treats those as private. So all classes that start with
        an underscore will be filtered out from running, this allows us to
        easily create base TestCase instances and not worry about them being
        run

        :param testnames: the test methods from `testCaseClass` that should
            be filtered, if this is empty then all test names will be found
            just like parent does
        """
        if testCaseClass.__name__.startswith("_"):
            testnames = []

        else:
            if not testnames:
                testnames = super().getTestCaseNames(testCaseClass)

        if testnames:
            if ignored := self.program.ignore_testpaths:
                testnames = [
                    n for n in testnames
                    if testpath(testCaseClass, n) not in ignored
                ]

        return testnames


class TestResult(TextTestResult):
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


class TestRunner(TextTestRunner):
    """
    https://docs.python.org/3/library/unittest.html#unittest.TextTestRunner
    https://github.com/python/cpython/blob/3.7/Lib/unittest/runner.py
    """
    resultclass = TestResult

    def _makeResult(self):
        result = super()._makeResult()
        result.program = self.program
        return result

    def _get_line_number(self, testcase: TestCase, failure: str) -> int:
        """Get the line number where the test failed"""

        # This feels like a terrible way to do this but I couldn't think of a
        # better way to do it
        if tc_path := inspect.getfile(type(testcase)):
            for line in failure.splitlines():
                if tc_path in line:
                    if m := re.search(r"line (\d+)", line):
                        return int(m.group(1))

                    else:
                        raise ValueError("Line formatting has changed")

        return 0

    def run(self, test):
        # this will be used to set the TestProgram instance into TestResult
        self.program = test.program

        test_cases = []
        if self.verbosity > 1:
            test_cases = list(test.get_testcases())

        result = super().run(test)

        if self.verbosity > 1:
            total_count = test.countTestCases()

            if len(test_cases) > 1:
#                 t_names = {}
#                 for tc in test_cases:
#                     class_name = tc.__class__.__qualname__
#                     class_key = f"{tc.__class__.__module__}.{class_name}"
#                     t_names[class_key] = [0, 0.0, class_name]

                t_names = {
                    classpath(tc): [0, 0.0, tc.__class__.__qualname__]
                    for tc in test_cases
                }
                class_type = "classes"

                if len(t_names) > 30:
                    t_names = {
                        tc.__class__.__module__: [
                            0,
                            0.0,
                            tc.__class__.__module__,
                        ]
                        for tc in test_cases
                    }
                    class_type = "modules"

                if len(t_names) > 1:
                    # print out how many ran to total tests
                    # https://github.com/Jaymon/pyt/issues/48
                    ran_count = result.testsRun

                    self.stream.writeln("")
                    self.stream.writeln(
                        f"Ran {ran_count}/{total_count} tests"
                        f" across {len(t_names)} {class_type}:",
                    )

                    for tn, duration in result.collectedDurations:
                        for tc_key in t_names.keys():
                            if tc_key in tn:
                                t_names[tc_key][0] += 1
                                t_names[tc_key][1] += duration

                    for _, tc_info in t_names.items():
                        tc, td, tc_name = tc_info
                        v = "tests" if tc > 1 else "test"
                        self.stream.writeln(
                            f"* {tc_name} - {tc} {v} in {td:.3f}s",
                        )

                    self.stream.writeln("")

            if len(result.errors) or len(result.failures):
                with RerunFile() as fp:
                    count = len(result.errors) + len(result.failures)
                    self.stream.writeln(
                        f"Failed or errored {count}/{total_count} tests:"
                    )

                    for testcase, failure in itertools.chain(
                        result.errors,
                        result.failures,
                    ):
                        tp = testpath(testcase)
                        if ln := self._get_line_number(testcase, failure):
                            self.stream.writeln(f"* {tp} on line {ln}")

                        else:
                            self.stream.writeln(f"* {tp}")

                        fp.writeln(tp)

                self.stream.writeln("")

            if len(result.skipped):
                self.stream.writeln(
                    f"Skipped {len(result.skipped)}/{total_count} tests:"
                )
                for testcase, failure in result.skipped:
                    self.stream.writeln(f"* {testpath(testcase)}")
                self.stream.writeln("")

        return result


class TestProgram(TestProgram):
    """The main entrypoint into the module, this is where everything starts

    https://docs.python.org/3/library/unittest.html#unittest.main
    https://github.com/python/cpython/blob/3.7/Lib/unittest/main.py
    """
    @property
    def verbosity(self):
        """We do some soft overriding of the parent parser's verbose flag"""
        return self._verbosity

    @verbosity.setter
    def verbosity(self, v):
        self._verbosity = v

        logger_name = modname()
        logger = logging.getLogger(logger_name)

        # https://docs.python.org/3/library/logging.html#logging.Logger.hasHandlers
        if not logger.hasHandlers():
        #if len(logger.handlers) == 0:
            log_handler = logging.StreamHandler(stream=sys.stderr)
            log_formatter = logging.Formatter("[%(levelname).1s] %(message)s")
            log_handler.setFormatter(log_formatter)
            logger.addHandler(log_handler)
            # https://docs.python.org/3/library/logging.html#logging.Logger.propagate
            #
            # we turn off propogation for pyt loggers because without this if
            # the tests that get loaded configured logging (which I commonly
            # do) then pyt would start double printing everything
            logger.propagate = False

        if v < 2:
            logger.setLevel(logging.WARNING)

        else:
            logger.setLevel(logging.DEBUG)

    def __init__(self, **kwargs):
        """Create a Pyt testing program

        Any flags defined on the parent class can be passed into here

        :keyword environ: TestEnviron, the testing environment
        :keyword testLoader: TestLoader
        :keyword testRunner: TestRunner
        """
        self.environ = kwargs.pop("environ", TestEnviron())

        if "testLoader" not in kwargs:
            # according to the code, testLoader gets defaulted to
            # unittest.loader.defaultTestLoader which is an instance, so to
            # override it we should pass in our loader as an instance also
            testloader = TestLoader()
            # we want to keep open the possibility of grabbing values from this
            # later on down the line
            testloader.program = self

            kwargs["testLoader"] = testloader

        # according to the code testRunner is defaulted to None and set to a
        # class in .runTests, where an instance is then created, so there are
        # no hooks to customize creation of it, it does pass .test into its
        # .run method though, so the customization hook will have to be there
        kwargs.setdefault("testRunner", TestRunner)

        # By default module is set to "__name__", this gets rid of that
        kwargs.setdefault("module", None)

        # anything after this line will not be run because once we enter into
        # the parent's __init__ then it begins to actually compile and call all
        # the tests, it must call .runTests which can call sys.exit
        super().__init__(**kwargs)

    def createTests(
        self,
        from_discovery: bool = False,
        Loader: type[TestLoader]|None = None,
    ) -> None:
        """Ideally we would put a lot of this configuration in .parseArgs but
        that method calls this method or `._do_discovery`, which then calls
        this method"""
        if not from_discovery:
            if self.rerun_failed_tests:
                if (
                    self.testNames
                    and (
                        len(self.testNames) > 1
                        or self.testNames[0] != ""
                    )
                ):
                    raise ValueError(
                        "Rerun flag passed in with tests arguments",
                    )

                else:
                    self.testNames = list(RerunFile())

            # if the --prefix flag was used on the command line then ignore the
            # environment prefixes
            if not self.prefixes:
                self.prefixes = self.environ.get_prefixes()

            self.ignore_testpaths = None
            if self.ignore_tests:
                if Loader is None:
                    Loader = type(self.testLoader)

                loader = Loader()
                loader.program = self
                self.ignore_testpaths = set(
                    loader.loadTestsFromNames(
                        _convert_names(self.ignore_tests),
                    ).get_testpaths(),
                )

        # `.testLoader` is used to load the tests and .test is set in parent's 
        # `.createTest` method
        super().createTests(
            from_discovery=from_discovery,
            Loader=Loader,
        )

    def _getParentArgParser(self) -> argparse.ArgumentParser:
        """Get the argument parser and add any custom flags

        .. note:: any flag you define will be set as an instance attribute
            because `self` is passed into the parser's `.parse_args`
            method as the Namespace object
        """
        from . import __version__ # avoid circular dependency

        parser = super()._getParentArgParser()

        parser.add_argument(
            "--version", "-V",
            action="version",
            version="%(prog)s {}, Python {} ({})".format(
                __version__,
                platform.python_version(),
                sys.executable,
            ),
        )

        # this exposes parent's warning setting to the CLI
        parser.add_argument(
            "--warnings", "--warning", "-w", "-W",
            dest="warnings",
            action="store_const",
            const="error",
            default=self.warnings,
            help="Converts warnings into errors",
        )

        parser.add_argument(
            "--rerun", "-r", "-R",
            dest="rerun_failed_tests",
            action="store_true",
            help="Rerun previously failed tests",
        )

        parser.add_argument(
            "--prefix", "-P",
            dest="prefixes",
            action="append",
            default=[],
            help=(
                "The prefix(es)"
                " (python module paths where TestCase subclasses are found)"
            ),
        )

        parser.add_argument(
            "--list", "-L",
            dest="list_found_tests",
            action="store_true",
            help="print out found tests",
        )

        parser.add_argument(
            "--skip", "-S", "--not", "-n",
            dest="ignore_tests",
            action="append",
            default=[],
            metavar="TEST",
            help="Invert the match and don't run those tests",
        )

        return parser

    def _getMainArgParser(
        self,
        parent: argparse.ArgumentParser,
    ) -> argparse.ArgumentParser:
        parser = super()._getMainArgParser(parent)

        # if we didn't pass in any test names then we want to find all tests
        # which would be the empty value, we need to set the `.tests` like
        # this to short circuit parent's routing to try and load tests from
        # a module or to call `._do_discovery` if no tests were passed in.
        parser.set_defaults(tests=[""])
        return parser

    def runTests(self):
        """This is the final method, if .exit=True then this will even exit
        the run when finished.

        This is the best place to add functionality that needs the flags all
        to be parsed but can interrupt the normal testing flow (like the
        `--list` flag that is implemented in here
        """
        if self.list_found_tests:
            testRunner = self.testRunner()
            testRunner.stream.write(self.test.get_method_names())
            testRunner.stream.writeln("")

            if self.exit:
                self._main_parser.exit()

        else:
            return super().runTests()

