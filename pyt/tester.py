# -*- coding: utf-8 -*-
# https://docs.python.org/2/library/unittest.html
from __future__ import unicode_literals
import re
import os
import unittest
from unittest.util import strclass
import sys
import inspect
import importlib
#from StringIO import StringIO
import time
from collections import Counter

from . import echo
from .compat import *


class TestEnviron(object):
    stdout_stream = sys.stdout
    stderr_stream = sys.stderr

    stdout_buffer = StringIO()
    stderr_buffer = StringIO()

    _instance = None
    """singleton"""

    def __init__(self, args=None):
        self.buffer = False
        self.debug = False
        self.args = args
        if args:
            self.debug = args.debug
            self.buffer = args.buffer

        self.init_buf()
        self.counter = Counter()
        echo.configure(self)

    @classmethod
    def get_instance(cls, args=None):
        if args or not cls._instance:
            cls._instance = cls(args)
        return cls._instance

    def init_buf(self):
        if self.buffer:
            sys.stdout = self.stdout_buffer
            sys.stderr = self.stderr_buffer

    def unbuffer(self):
        if sys.stdout is not self.stdout_stream:
            sys.stdout = self.stdout_stream

        if sys.stderr is not self.stderr_stream:
            sys.stderr = self.stderr_stream

    def update_env_for_test(self, test_count):
        # not sure how much I love messing with the environment right here, but this
        # does propagate down to the test cases
        os.environ['PYT_TEST_COUNT'] = str(test_count)
        os.environ['PYT_TEST_METHOD_COUNT'] = str(self.counter["methods"])
        os.environ['PYT_TEST_CLASS_COUNT'] = str(self.counter["classes"])
        os.environ['PYT_TEST_MODULE_COUNT'] = str(self.counter["modules"])


class TestInfo(object):
    def __init__(self, name, basedir, method_prefix='test', **kwargs):
        self.name = name
        self.basedir = basedir
        self.method_prefix = method_prefix
        self.set_possible()

    def raise_any_error(self):
        """raise any found error in the possible TestCaseInfos"""
        for tc in self.possible:
            tc.raise_found_error()

    def set_possible(self):
        '''
        break up a module path to its various parts (prefix, module, class, method)

        this uses PEP 8 conventions, so foo.Bar would be foo module with class Bar

        return -- list -- a list of possible interpretations of the module path
            (eg, foo.bar can be bar module in foo module, or bar method in foo module)
        '''
        possible = []
        name = self.name
        name_f = self.name.lower()
        filepath = ""
        if name_f.endswith(".py") or ".py:" in name_f:
            # path/something:Class.method
            bits = name.split(":", 1)
            filepath = bits[0]
            name = bits[1] if len(bits) > 1 else ""
            echo.debug('Found filepath: {}', filepath)

        bits = name.split('.')
        basedir = self.basedir
        method_prefix = self.method_prefix

        # check if the last bit is a Class
        if re.search(r'^[A-Z]', bits[-1]):
            echo.debug('Found class in name: {}', bits[-1])
            possible.append(TestCaseInfo(basedir, method_prefix, **{
                'class_name': bits[-1],
                'module_name': bits[-2] if len(bits) > 1 else '',
                'prefix': os.sep.join(bits[0:-2]),
                'filepath': filepath,
            }))
        elif len(bits) > 1 and re.search(r'^[A-Z]', bits[-2]):
            echo.debug('Found class in name: {}', bits[-2])
            possible.append(TestCaseInfo(basedir, method_prefix, **{
                'class_name': bits[-2],
                'method_name': bits[-1],
                'module_name': bits[-3] if len(bits) > 2 else '',
                'prefix': os.sep.join(bits[0:-3]),
                'filepath': filepath,
            }))
        else:
            if self.name:
                echo.debug('name is ambiguous')
                possible.append(TestCaseInfo(basedir, method_prefix, **{
                    'module_name': bits[-1],
                    'prefix': os.sep.join(bits[0:-1]),
                    'filepath': filepath,
                }))
                possible.append(TestCaseInfo(basedir, method_prefix, **{
                    'method_name': bits[-1],
                    'module_name': bits[-2] if len(bits) > 1 else '',
                    'prefix': os.sep.join(bits[0:-2]),
                    'filepath': filepath,
                }))

            else:
                possible.append(TestCaseInfo(basedir, method_prefix, filepath=filepath))

        self.possible = possible


class TestCaseInfo(object):
    def __init__(self, basedir, method_prefix='test', **kwargs):
        self.basedir = basedir
        self.method_prefix = method_prefix
        for k, v in kwargs.items():
            setattr(self, k, v)

    def has_module(self):
        v = getattr(self, 'module_name', None)
        return bool(v)

    def has_class(self):
        v = getattr(self, 'class_name', None)
        return bool(v)

    def has_method(self):
        v = getattr(self, 'method_name', None)
        return bool(v)

    def __str__(self):
        ret = ''
        for k in ['prefix', 'module_name', 'class_name', 'method_name']:
            v = getattr(self, k, None)
            if v:
                ret += "{}: {}, ".format(k, v)

        return ret.rstrip(', ')

    def raise_found_error(self):
        """raise an error if one was found, otherwise do nothing"""
        error_info = getattr(self, 'error_info', None)
        if error_info:

            reraise(*error_info)

#             if py_2:
#                 #raise error_info[0].__class__, error_info[0], error_info[1][2]
#                 reraise(*error_info)
#                 #raise error_info[0].__class__, error_info[1], error_info[2]
# 
#             elif py_3:
#                 #e, exc_info = error_info
#                 #et, ei, tb = exc_info
# 
#                 reraise(*error_info)
#                 #et, ei, tb = error_info
#                 #raise ei.with_traceback(tb)

    def modules(self):
        """return modules that match module_name"""
        # this is a hack because I couldn't get imp.load_source to work right
        sys.path.insert(0, self.basedir)
        for p in self.paths():
            # http://stackoverflow.com/questions/67631/
            try:
                module_name = self.module_path(p)
                m = importlib.import_module(module_name)
                yield m

            except Exception as e:
                echo.debug('Caught exception while importing {}: {}', p, e)
                error_info = getattr(self, 'error_info', None)
                if not error_info:
                    exc_info = sys.exc_info()
                    #raise e.__class__, e, exc_info[2]
                    #self.error_info = (e, exc_info)
                    self.error_info = exc_info
                continue

        sys.path.pop(0)

    def classes(self):
        """the partial self.class_name will be used to find actual TestCase classes"""
        for module in self.modules():
            cs = inspect.getmembers(module, inspect.isclass)
            class_name = getattr(self, 'class_name', '')
            class_regex = ''
            if class_name:
                class_regex = re.compile(r'^{}'.format(class_name), re.I)

            for c_name, c in cs:
                can_yield = True
                if class_regex and not class_regex.match(c_name):
                #if class_name and class_name not in c_name:
                    can_yield = False

                if can_yield and issubclass(c, unittest.TestCase):
                    if c is not unittest.TestCase: # ignore actual TestCase class
                        echo.debug('class: {}', c_name)
                        yield c

    def method_names(self):
        """return the actual test methods that matched self.method_name"""
        for c in self.classes():
            #ms = inspect.getmembers(c, inspect.ismethod)
            # http://stackoverflow.com/questions/17019949/
            ms = inspect.getmembers(c, lambda f: inspect.ismethod(f) or inspect.isfunction(f))
            method_name = getattr(self, 'method_name', '')
            method_regex = ''
            if method_name:
                if method_name.startswith(self.method_prefix):
                    method_regex = re.compile(r'^{}'.format(method_name), re.I)

                else:
                    method_regex = re.compile(
                        r'^{}[_]{{0,1}}{}'.format(self.method_prefix, method_name),
                        re.I
                    )

            for m_name, m in ms:
                if not m_name.startswith(self.method_prefix): continue

                can_yield = True
                if method_regex and not method_regex.match(m_name):
                    can_yield = False

                if can_yield:
                    echo.debug('method: {}', m_name)
                    yield c, m_name

    def paths(self):
        '''
        given a basedir, yield all test modules paths recursively found in
        basedir that are test modules

        return -- generator
        '''
        module_name = getattr(self, 'module_name', '')
        module_prefix = getattr(self, 'prefix', '')
        basedir = self.basedir
        filepath = getattr(self, 'filepath', '')

        if filepath:
            if os.path.isabs(filepath):
                yield filepath

            else:
                yield os.path.join(basedir, filepath)

        else:
            module_regex = ''
            package_regex = ''
            if module_name:
                if module_name.startswith('test') or module_name.endswith('test'):
                    module_regex = re.compile(
                        r'^{}\.py$'.format(module_name),
                        re.I
                    )
                    package_regex = re.compile(
                        r'^{}|{}$'.format(module_name, module_name),
                        re.I
                    )

                else:
                    module_regex = re.compile(
                        r'^(?:test_?{}|{}.*?_?test)\.py$'.format(module_name, module_name),
                        re.I
                    )
                    package_regex = re.compile(
                        r'^(?:test_?{}|{}.*?_?test)$'.format(module_name, module_name),
                        re.I
                    )

            else:
                module_regex = re.compile(r'^(?:test\S+|\S+test)\.py$', re.I)
                package_regex = re.compile(r'^(?:test\S+|\S+test)$', re.I)

            prefix_regex = ''
            if module_prefix:
                #prefix_regex = re.compile(module_prefix.replace('.', '[\\/]'), re.I)
                prefix_regex = re.compile(module_prefix, re.I)

            seen_paths = set()
            for root, dirs, files in os.walk(basedir, topdown=True):
                dirs[:] = [d for d in dirs if d[0] != '.'] # ignore dot directories
                if prefix_regex:
                    if not prefix_regex.search(root): continue

                for f in files:
                    if module_regex.search(f):
                        filepath = os.path.join(root, f)
                        if filepath not in seen_paths:
                            echo.debug('Module path: {}', filepath)
                            seen_paths.add(filepath)
                            yield filepath

                    elif f.startswith("__init__") and package_regex.search(os.path.basename(root)):
                        pmodule_regex = re.compile(r'.py$', re.I)
                        for proot, pdirs, pfiles in os.walk(root, topdown=True):
                            pdirs[:] = [d for d in dirs if d[0] != '.']
                            for pf in pfiles:
                                if pmodule_regex.search(pf):
                                    filepath = os.path.join(proot, pf)
                                    if filepath not in seen_paths:
                                        echo.debug('Submodule path: {}', filepath)
                                        seen_paths.add(filepath)
                                        yield filepath

    def module_path(self, filepath):
        """given a filepath like /base/path/to/module.py this will convert it to
        path.to.module so it can be imported"""
        basedir = self.basedir
        module_name = filepath.replace(basedir, '', 1)
        module_name = module_name.strip('\\/')

        # remove all dirs that don't have an __init__.py file (ie, they're not modules)
        modules = re.split('[\\/]', module_name)
        module_count = len(modules)
        if module_count > 1:
            for x in range(module_count):
                path_args = [basedir]
                path_args.extend(modules[0:x + 1])
                path_args.append('__init__.py')
                module_init = os.path.join(*path_args)
                if os.path.isfile(module_init): break

            if x > 1:
                echo.debug(
                    'Removed {} from {} because is is not a python module',
                    os.sep.join(modules[0:x]), module_name
                )

            module_name = '.'.join(modules[x:])

        # convert the remaining file path to a python module path that can be imported
        module_name = re.sub(r'(?:\.__init__)?\.py$', '', module_name, flags=re.I)
        return module_name


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
                lines.append("{}.{}".format(strclass(test.__class__), test._testMethodName))

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
        ti = TestInfo(name, self.basedir, self.testMethodPrefix)
        found = False
        for i, tc in enumerate(ti.possible, 1):
            echo.debug("{}. Searching for tests matching:", i)
            echo.debug("    {}", tc)
            if tc.has_method():
                for c, mn in tc.method_names():
                    #echo.debug('adding test method to suite: {}', mn)
                    #echo.out('Found method test: {}.{}.{}', c.__module__, c.__name__, mn)
                    echo.debug('Found method test: {}.{}', strclass(c), mn)
                    found = True
                    ts.addTest(c(mn))
                    self.environ.counter["methods"] += 1

            elif tc.has_class():
                for c in tc.classes():
                    #echo.debug('adding testcase to suite: {}', c.__name__)
                    #echo.out('Found class test: {}.{}', c.__module__, c.__name__)
                    echo.debug('Found class test: {}', strclass(c))
                    found = True
                    ts.addTest(self.loadTestsFromTestCase(c))
                    self.environ.counter["classes"] += 1

            else:
                for m in tc.modules():
                    #echo.debug('adding module to suite: {}', m.__name__)
                    echo.debug('Found module test: {}', m.__name__)
                    found = True
                    ts.addTest(self.loadTestsFromModule(m))
                    self.environ.counter["modules"] += 1

                # if we found a module that matched then don't try for method
                if found: break

        if not found:
            ti.raise_any_error()

        echo.debug("Found {} total tests".format(ts.countTestCases()))
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

        echo.debug("{}/{} - Starting {}.{}".format(
            self.testsRun + 1,
            self.total_tests,
            strclass(test.__class__),
            test._testMethodName
        ))
        super(TestResult, self).startTest(test)

    def stopTest(self, test):
        """ran once after each TestCase"""
        super(TestResult, self).stopTest(test)

        pyt_start = self._pyt_start
        del(self._pyt_start)

        pyt_stop = time.time()

        echo.debug("Stopping {}.{} after {}s".format(
            strclass(test.__class__),
            test._testMethodName,
            round(pyt_stop - pyt_start, 2)
        ))

    def __init__(self, *args, **kwargs):
        super(TestResult, self).__init__(*args, **kwargs)
        self._original_stdout = TestEnviron.stdout_stream
        self._original_stderr = TestEnviron.stderr_stream
        self._stdout_buffer = TestEnviron.stdout_buffer
        self._stderr_buffer = TestEnviron.stderr_buffer


# https://hg.python.org/cpython/file/648dcafa7e5f/Lib/unittest/runner.py
class TestRunner(unittest.TextTestRunner):
    """
    This sets our custom result class and also makes sure the stream that gets passed
    to the runner is the correct stderr stream and not a buffered stream, so it can
    still print out the test information even though it buffers everything else, just
    like how it is done with the original unittest
    """
    resultclass = TestResult

    def __init__(self, *args, **kwargs):
        self.environ = TestEnviron.get_instance()
        stream = self.environ.stderr_stream
        super(TestRunner, self).__init__(
            stream=stream,
            *args,
            **kwargs
        )

#     def __init__(self, stream=None, *args, **kwargs):
#         if not stream:
#             stream = self.resultclass.stderr_stream
#         super(TestRunner, self).__init__(stream=stream, *args, **kwargs)

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


def run_test(name, basedir, **kwargs):
    '''
    run the test found with find_test() with unittest

    **kwargs -- dict -- all other args to pass to unittest
    '''
    ret_code = 0

    environ = TestEnviron.get_instance()
    tl = TestLoader(basedir, environ)

    kwargs.setdefault('argv', ['run_test'])
    kwargs['argv'].append(name)

    kwargs.setdefault('exit', False)
    kwargs.setdefault('testLoader', tl)
    kwargs.setdefault('testRunner', TestRunner)
    #kwargs.setdefault('testRunner', tr)

    # https://docs.python.org/2/library/unittest.html#unittest.main
    try:
        ret = unittest.main(**kwargs)
        if len(ret.result.errors) or len(ret.result.failures):
            ret_code = 1

        elif not ret.result.testsRun:
            ret_code = 1

        echo.debug('Test returned: {}', ret_code)

    finally:
        environ.unbuffer()

    return ret_code


