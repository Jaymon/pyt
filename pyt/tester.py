# -*- coding: utf-8 -*-
# https://docs.python.org/2/library/unittest.html
from __future__ import unicode_literals, division, print_function, absolute_import
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
import logging
import hashlib
import warnings

from .compat import *


logging.basicConfig(format="%(message)s", level=logging.WARNING, stream=sys.stderr)
logger = logging.getLogger(__name__)


class TestEnviron(object):
    stdout_stream = sys.stdout
    stderr_stream = sys.stderr

    stdout_buffer = StringIO()
    stderr_buffer = StringIO()

    _instance = None
    """singleton"""

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, v):
        if v:
            logger.setLevel(logging.DEBUG)
            # stddbg = environ.stderr_stream
        else:
            logger.setLevel(logging.WARNING)
        self._debug = v

    def __init__(self, args=None):
        self.buffer = False
        self.debug = False
        self.warnings = False
        self.args = args
        if args:
            self.debug = args.debug
            self.buffer = args.buffer
            self.warnings = args.warnings

        self.init_buf()
        self.counter = Counter()

#         if self.debug:
#             logger.setLevel(logging.DEBUG)

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


class PathGuesser(object):
    """PathGuesser

    This class compiles the possible paths, it is created in the TestLoader and then 
    the .possible attribute is iterated to actually load the tests.

    The .possible property consists of PathFinder objects
    """
    def __init__(self, name, basedir, method_prefix='test', **kwargs):
        self.name = name
        self.basedir = basedir
        self.method_prefix = method_prefix
        self.set_possible()

    def raise_any_error(self):
        """raise any found error in the possible PathFinders"""
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
            logger.debug('Found filepath: {}'.format(filepath))

        bits = name.split('.')
        basedir = self.basedir
        method_prefix = self.method_prefix

        # check if the last bit is a Class
        if re.search(r'^[A-Z]', bits[-1]):
            logger.debug('Found class in name: {}'.format(bits[-1]))
            possible.append(PathFinder(basedir, method_prefix, **{
                'class_name': bits[-1],
                'module_name': bits[-2] if len(bits) > 1 else '',
                'prefix': os.sep.join(bits[0:-2]),
                'filepath': filepath,
            }))
        elif len(bits) > 1 and re.search(r'^[A-Z]', bits[-2]):
            logger.debug('Found class in name: {}'.format(bits[-2]))
            possible.append(PathFinder(basedir, method_prefix, **{
                'class_name': bits[-2],
                'method_name': bits[-1],
                'module_name': bits[-3] if len(bits) > 2 else '',
                'prefix': os.sep.join(bits[0:-3]),
                'filepath': filepath,
            }))
        else:
            if self.name:
                logger.debug('Name is ambiguous')
                possible.append(PathFinder(basedir, method_prefix, **{
                    'module_name': bits[-1],
                    'prefix': os.sep.join(bits[0:-1]),
                    'filepath': filepath,
                }))
                possible.append(PathFinder(basedir, method_prefix, **{
                    'method_name': bits[-1],
                    'module_name': bits[-2] if len(bits) > 1 else '',
                    'prefix': os.sep.join(bits[0:-2]),
                    'filepath': filepath,
                }))
                possible.append(PathFinder(basedir, method_prefix, **{
                    'prefix': os.sep.join(bits),
                    'filepath': filepath,
                }))

            else:
                possible.append(PathFinder(basedir, method_prefix, filepath=filepath))

        self.possible = possible


class PathFinder(object):
    """Pathfinder class

    this is where all the magic happens, PathGuesser guesses on what the paths might
    be and creates instances of this class, those instances then actually validate
    the guesses and allow the tests to be loaded or not
    """
    def __init__(self, basedir, method_prefix='test', **kwargs):
        self.basedir = basedir
        self.method_prefix = method_prefix
        self.module_prefixes = ["test_", "test"]
        self.module_postfixes = ["_test", "test", "_tests", "tests"]
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

    def modules(self):
        """return modules that match module_name"""
        # this is a hack because I couldn't get imp.load_source to work right
        #sys.path.insert(0, self.basedir)
        for p in self.paths():
            # http://stackoverflow.com/questions/67631/
            try:
#                 module_name = self.module_path(p)
#                 m = import_path(p)
#                 m.__name__ = module_name
#                 pout.v(m.__name__)


                module_name = self.module_path(p)
                m = importlib.import_module(module_name)

                # I don't really like this solution, it seems like a hacky way
                # to solve: https://github.com/Jaymon/pyt/issues/24
                if is_py2:
                    module_hash = hashlib.md5(str(p)).hexdigest()
                else:
                    module_hash = hashlib.md5(str(p).encode("utf-8")).hexdigest()
                sys.modules[module_hash] = sys.modules.pop(module_name)

                yield m

            except Exception as e:
                logger.warning('Caught exception while importing {}: {}'.format(p, e))
                logger.warning(e, exc_info=True)
                error_info = getattr(self, 'error_info', None)
                if not error_info:
                    exc_info = sys.exc_info()
                    #raise e.__class__, e, exc_info[2]
                    #self.error_info = (e, exc_info)
                    self.error_info = exc_info
                continue

        #sys.path.pop(0)

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
                        logger.debug('class: {}'.format(c_name))
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
                    logger.debug('method: {}'.format(m_name))
                    yield c, m_name

    def _find_basename(self, name, basenames, is_prefix=False):
        """check if name combined with test prefixes or postfixes is found anywhere
        in the list of basenames

        :param name: string, the name you're searching for
        :param basenames: list, a list of basenames to check
        :param is_prefix: bool, True if this is a prefix search, which means it will
            also check if name matches any of the basenames without the prefixes or
            postfixes, if it is False then the prefixes or postfixes must be present
            (ie, the module we're looking for is the actual test module, not the parent
             modules it's contained in)
        :returns: string, the basename if it is found
        """
        ret = ""
        fileroots = [(os.path.splitext(n)[0], n) for n in basenames]
        glob = False
        if name.startswith("*"):
            glob = True
        name = name.strip("*")

        for fileroot, basename in fileroots:
            if name in fileroot or fileroot in name:
                for pf in self.module_postfixes:
                    logger.debug(
                        'Checking if basename {} starts with {} and ends with {}'.format(
                        basename,
                        name,
                        pf
                    ))
                    if glob:
                        if name in fileroot and fileroot.endswith(pf):
                            ret = basename
                            break
                    else:
                        if fileroot.startswith(name) and fileroot.endswith(pf):
                            ret = basename
                            break

                if not ret:
                    for pf in self.module_prefixes:
                        n = pf + name
                        logger.debug('Checking if basename {} starts with {}'.format(basename, n))
                        if glob:
                            if fileroot.startswith(pf) and name in fileroot:
                                ret = basename
                                break
                        else:
                            if fileroot.startswith(n):
                                ret = basename
                                break

                if not ret:
                    if is_prefix:
                        logger.debug('Checking if basename {} starts with {}'.format(basename, name))
                        if basename.startswith(name) or (glob and name in basename):
                            ret = basename

                        else:
                            logger.debug(
                                'Checking if basename {} starts with {} and is a test module'.format(
                                basename,
                                name
                            ))
                            if glob:
                                if name in basename and self._is_module_path(basename):
                                    ret = basename

                            else:
                                if basename.startswith(name) and self._is_module_path(basename):
                                    ret = basename

                if ret:
                    logger.debug('Found basename {}'.format(ret))
                    break

        return ret

    def _find_prefix_paths(self, basedir, prefix):
        ret = basedir
        modnames = re.split(r"[\.\/]", prefix)
        seen_paths = set()

        for root, dirs, files in self.walk(basedir):
            logger.debug("Checking {} for prefix {}".format(root, prefix))
            ret = root
            for modname in modnames:
                for root2, dirs2, files2 in self.walk(ret):
                    logger.debug("Checking {} for modname {}".format(root2, modname))
                    ret = ""
                    basename = self._find_basename(modname, dirs2, is_prefix=True)
                    if basename:
                        ret = os.path.join(root2, basename)
                        logger.debug("Found prefix path {}".format(ret))
                        break

                if not ret:
                    logger.debug("Could not find a prefix path in {} matching {}".format(root, modname))
                    break

            if ret:
                if ret not in seen_paths:
                    seen_paths.add(ret)
                    logger.debug("Yielding prefix path {}".format(ret))
                    yield ret

    def _find_prefix_path(self, basedir, prefix):
        """Similar to _find_prefix_paths() but only returns the first match"""
        ret = ""
        for ret in self._find_prefix_paths(basedir, prefix):
            break

        if not ret:
            raise IOError("Could not find prefix {} in path {}".format(prefix, basedir))

        return ret

    def _find_module_path(self, basedir, modname):
        ret = ""

        try:
            ret = self._find_prefix_path(basedir, modname)

        except IOError:
            logger.debug('Checking for a module that matches {} in {}'.format(modname, basedir))
            for root, dirs, files in self.walk(basedir):
                basename = self._find_basename(modname, files, is_prefix=False)
                if basename:
                    ret = os.path.join(root, basename)
                    break



                for basename in files:
                    fileroot = os.path.splitext(basename)[0]
                    if fileroot in modname or modname in fileroot:
                        for pf in self.module_postfixes:
                            n = modname + pf
                            logger.debug('Checking {} against {}'.format(n, fileroot))
                            if fileroot.startswith(n):
                                ret = os.path.join(root, basename)
                                break

                        if not ret:
                            for pf in self.module_prefixes:
                                n = pf + modname
                                logger.debug('Checking {} against {}'.format(n, fileroot))
                                if fileroot.startswith(n):
                                    ret = os.path.join(root, basename)
                                    break

                        if not ret:
                            if self._is_module_path(basename) and modname == basename:
                                ret = os.path.join(root, basename)
                                break

                    if ret: break
                if ret: break

        if not ret:
            raise IOError("Could not find a module path with {}".format(modname))

        logger.debug("Found module path {}".format(ret))
        return ret

    def _is_module_path(self, path):
        """Returns true if the passed in path is a test module path

        :param path: string, the path to check, will need to start or end with the
            module test prefixes or postfixes to be considered valid
        :returns: boolean, True if a test module path, False otherwise
        """
        ret = False
        basename = os.path.basename(path)
        fileroot = os.path.splitext(basename)[0]
        for pf in self.module_postfixes:
            if fileroot.endswith(pf):
                ret = True
                break

        if not ret:
            for pf in self.module_prefixes:
                if fileroot.startswith(pf):
                    ret = True
                    break
        return ret



    def walk(self, basedir):
        """Walk all the directories of basedir except hidden directories

        :param basedir: string, the directory to walk
        :returns: generator, same as os.walk
        """
        for root, dirs, files in os.walk(basedir, topdown=True):
            dirs[:] = [d for d in dirs if d[0] != '.'] # ignore dot directories
            yield root, dirs, files

    def paths(self):
        '''
        given a basedir, yield all test modules paths recursively found in
        basedir that are test modules

        return -- generator
        '''
        module_name = getattr(self, 'module_name', '')
        module_prefix = getattr(self, 'prefix', '')
        filepath = getattr(self, 'filepath', '')

        if filepath:
            if os.path.isabs(filepath):
                yield filepath

            else:
                yield os.path.join(self.basedir, filepath)

        else:
            if module_prefix:
                basedirs = self._find_prefix_paths(self.basedir, module_prefix)
            else:
                basedirs = [self.basedir]

            for basedir in basedirs:
                try:
                    if module_name:
                        path = self._find_module_path(basedir, module_name)

                    else:
                        path = basedir

                    if os.path.isfile(path):
                        logger.debug('Module path: {}'.format(path))
                        yield path

                    else:
                        seen_paths = set()
                        for root, dirs, files in self.walk(path):
                            for basename in files:
                                if basename.startswith("__init__"):
                                    if self._is_module_path(root):
                                        filepath = os.path.join(root, basename)
                                        if filepath not in seen_paths:
                                            logger.debug('Module package path: {}'.format(filepath))
                                            seen_paths.add(filepath)
                                            yield filepath

                                else:
                                    fileroot = os.path.splitext(basename)[0]
                                    for pf in self.module_postfixes:
                                        if fileroot.endswith(pf):
                                            filepath = os.path.join(root, basename)
                                            if filepath not in seen_paths:
                                                logger.debug('Module postfix path: {}'.format(filepath))
                                                seen_paths.add(filepath)
                                                yield filepath

                                    for pf in self.module_prefixes:
                                        if fileroot.startswith(pf):
                                            filepath = os.path.join(root, basename)
                                            if filepath not in seen_paths:
                                                logger.debug('Module prefix path: {}'.format(filepath))
                                                seen_paths.add(filepath)
                                                yield filepath

                except IOError as e:
                    # we failed to find a suitable path
                    logger.warning(e, exc_info=True)
                    pass

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
                logger.debug(
                    'Removed {} from {} because is is not a python module'.format(
                    os.sep.join(modules[0:x]), module_name
                ))

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
        ti = PathGuesser(name, self.basedir, self.testMethodPrefix)
        found = False
        logger.debug("Searching for tests in directory: {}".format(self.basedir))
        for i, tc in enumerate(ti.possible, 1):
            logger.debug("{}. Searching for tests matching:".format(i))
            logger.debug("    {}".format(tc))
            if tc.has_method():
                for c, mn in tc.method_names():
                    logger.debug('Found method test: {}.{}'.format(strclass(c), mn))
                    found = True
                    ts.addTest(c(mn))
                    self.environ.counter["methods"] += 1

            elif tc.has_class():
                for c in tc.classes():
                    logger.debug('Found class test: {}'.format(strclass(c)))
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

        logger.debug("{}/{} - Starting {}.{}".format(
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

        logger.debug("Stopping {}.{} after {}s".format(
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


def run_test(name, basedir, **kwargs):
    '''
    run the test found with find_test() with unittest

    **kwargs -- dict -- all other args to pass to unittest
    '''
    ret_code = 0

    environ = TestEnviron.get_instance()
    tl = TestLoader(basedir, environ)

    kwargs.setdefault('argv', ['run_test'])
    kwargs['argv'] = kwargs['argv'] + [name]

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

        logger.debug('Test returned: {}'.format(ret_code))

    finally:
        environ.unbuffer()

    return ret_code


