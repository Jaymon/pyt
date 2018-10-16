# -*- coding: utf-8 -*-
# https://docs.python.org/2/library/unittest.html
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import unittest
import unittest.main
import time
import logging

from .compat import *
from .utils import testpath, classpath, chain
from .environ import TestEnviron
from .path import PathGuesser, PathFinder


logger = logging.getLogger(__name__)


# https://hg.python.org/cpython/file/tip/Lib/unittest/suite.py
class TestSuite(unittest.TestSuite):
    def addTest(self, test):
        """This will filter out "private" classes that begin with an underscore"""
        add_it = True
        if isinstance(test, unittest.TestCase):
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
class TestLoader(unittest.TestLoader):
    """
    https://docs.python.org/2/library/unittest.html#unittest.TestLoader
    """
    def __init__(self, basedir, environ):
        super(TestLoader, self).__init__()
        self.basedir = self.normalize_dir(basedir)
        self.suiteClass = TestSuite
        self.environ = environ

    def normalize_dir(self, d):
        '''
        get rid of things like ~/ and ./ on a directory

        d -- string
        return -- string -- d, now with 100% more absolute path
        '''
        d = os.path.expanduser(d)
        d = os.path.abspath(d)
        return d

#     def loadTestsFromModule(self, *args, **kwargs):
#         tests = super(TestLoader, self).loadTestsFromModule(*args, **kwargs)
#         pout.v(tests)
#         return tests

    def loadTestsFromName(self, name, *args, **kwargs):
        ts = self.suiteClass()
        ti = PathGuesser(name, self.basedir, self.testMethodPrefix)
        found = False
        logger.debug("Searching for tests in directory: {}".format(self.basedir))
        for i, tc in enumerate(ti.possible, 1):
            logger.debug("{}. Searching for tests matching:".format(i))
            logger.debug("    {}".format(tc))
            if tc.has_method():
                for c, mn in tc.method_names():
                    logger.debug('Found method test: {}'.format(testpath(c)))
                    found = True
                    ts.addTest(c(mn))
                    self.environ.counter["methods"] += 1

            elif tc.has_class():
                for c in tc.classes():
                    logger.debug('Found class test: {}'.format(classpath(c)))
                    found = True
                    ts.addTest(self.loadTestsFromTestCase(c))
                    self.environ.counter["classes"] += 1

            else:
                for m in tc.modules():
                    logger.debug('Found module test: {}'.format(m.__name__))
                    found = True
                    ts.addTest(self.loadTestsFromModule(m))
                    self.environ.counter["modules"] += 1

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
class TestResult(unittest.TextTestResult):
    """
    This is overridden so I can keep original copies of stdout and stderr, and also
    so I can have control over the stringIO instances that would be used if buffer is
    passed in. What was happening previously was our custom test loader would load
    all the testing modules before unittest had a chance to buffer them, so they would
    have real references to stdout/stderr and would still print out all the logging.
    """
    total_tests = 0

    def startTest(self, test):
        """ran once before each TestCase"""
        self._pyt_start = time.time()

        logger.debug("{}/{} - Starting {}".format(
            self.testsRun + 1,
            self.total_tests,
            testpath(test)
        ))
        super(TestResult, self).startTest(test)

    def stopTest(self, test):
        """ran once after each TestCase"""
        super(TestResult, self).stopTest(test)

        pyt_start = self._pyt_start
        del(self._pyt_start)

        pyt_stop = time.time()

        logger.debug("Stopping {} after {}s".format(
            testpath(test),
            round(pyt_stop - pyt_start, 2)
        ))

    def __init__(self, *args, **kwargs):
        super(TestResult, self).__init__(*args, **kwargs)
        self._original_stdout = TestEnviron.stdout_stream
        self._original_stderr = TestEnviron.stderr_stream
        self._stdout_buffer = TestEnviron.stdout_buffer
        self._stderr_buffer = TestEnviron.stderr_buffer


class TestRunner(unittest.TextTestRunner):
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
        stream = self.environ.stderr_stream
        super(TestRunner, self).__init__(
            stream=stream,
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
        return result


class TestProgram(unittest.main.TestProgram):
    """
    https://github.com/python/cpython/blob/3.7/Lib/unittest/main.py
    https://github.com/python/cpython/blob/2.7/Lib/unittest/main.py
    """
    def __init__(self, **kwargs):


main = TestProgram

def main(name="", basedir="", **kwargs):
    '''
    run the test found with find_test() with unittest

    **kwargs -- dict -- all other args to pass to unittest
    '''
    ret_code = 0


    # create the environment
    buf = kwargs.pop("buffer", False)
    warnings = kwargs.pop("warnings", False)
    environ = TestEnviron.get_instance(
        buffer=buf,
        warnings=warnings
    )

    tl = TestLoader(basedir, environ)

    #kwargs.setdefault('argv', [__name__.split(".")[0]])
    #kwargs['argv'] = kwargs['argv'] + [name]
    kwargs["argv"] = None
    kwargs["defaultTest"] = name

    kwargs.setdefault('exit', False)
    kwargs.setdefault('testLoader', tl)
    kwargs.setdefault('testRunner', TestRunner)
    #kwargs.setdefault('testRunner', tr)

    # https://docs.python.org/2/library/unittest.html#unittest.main
    try:
        ret = unittest.main(**kwargs)
        if len(ret.result.errors) or len(ret.result.failures):
            ret_code = 1

            # TODO: can we print skipped tests?
            logger.debug("Test failures/errors:")
            for testcase, failure in chain(ret.result.errors, ret.result.failures):
                logger.debug(testpath(testcase))

        elif not ret.result.testsRun:
            ret_code = 1

        logger.debug('Test returned: {}'.format(ret_code))

    finally:
        environ.unbuffer()

    return ret_code


