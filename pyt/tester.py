# -*- coding: utf-8 -*-
import argparse
import re
import os
import ast
import unittest
from unittest import TestCase # to allow from pyt import TestCase, Assert
import sys
import inspect
import imp
import importlib

from . import echo


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
        bits = self.name.split(u'.')
        basedir = self.basedir
        possible = []
        module_class = u''
        module_method = u''
        module_prefix = u''
        method_prefix = self.method_prefix

        # check if the last bit is a Class
        if re.search(ur'^[A-Z]', bits[-1]):
            echo.debug('Found class in name: {}', bits[-1])
            possible.append(TestCaseInfo(basedir, method_prefix, **{
                'class_name': bits[-1],
                'module_name': bits[-2] if len(bits) > 1 else u'',
                'prefix': os.sep.join(bits[0:-2])
            }))
        elif len(bits) > 1 and re.search(ur'^[A-Z]', bits[-2]):
            echo.debug('Found class in name: {}', bits[-2])
            possible.append(TestCaseInfo(basedir, method_prefix, **{
                'class_name': bits[-2],
                'method_name': bits[-1],
                'module_name': bits[-3] if len(bits) > 2 else u'',
                'prefix': os.sep.join(bits[0:-3])
            }))
        else:
            if self.name:
                echo.debug('name is ambiguous')
                possible.append(TestCaseInfo(basedir, method_prefix, **{
                    'module_name': bits[-1],
                    'prefix': os.sep.join(bits[0:-1])
                }))
                possible.append(TestCaseInfo(basedir, method_prefix, **{
                    'method_name': bits[-1],
                    'module_name': bits[-2] if len(bits) > 1 else u'',
                    'prefix': os.sep.join(bits[0:-2])
                }))

            else:
                possible.append(TestCaseInfo(basedir, method_prefix))

        self.possible = possible


class TestCaseInfo(object):
    def __init__(self, basedir, method_prefix='test', **kwargs):
        self.basedir = basedir
        self.method_prefix = method_prefix
        for k, v in kwargs.iteritems():
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
        ret = u''
        for k in ['prefix', 'module_name', 'class_name', 'method_name']:
            v = getattr(self, k, None)
            if v:
                ret += u"{}: {}, ".format(k, v)

        return ret.rstrip(', ')

    def raise_found_error(self):
        """raise an error if one was found, otherwise do nothing"""
        error_info = getattr(self, 'error_info', None)
        if error_info:
            raise error_info[0].__class__, error_info[0], error_info[1][2]

    def modules(self):
        """return modules that match module_name"""
        # this is a hack, I couldn't get imp.load_source to work right
        sys.path.insert(0, self.basedir)
        for p in self.paths():
            # http://stackoverflow.com/questions/67631/
            try:
                module_name = self.module_path(p)
                m = importlib.import_module(module_name)
                #m = imp.load_source(module_name, p)
                yield m

            except Exception, e:
                echo.debug('Caught exception while importing {}: {}', p, e)
                error_info = getattr(self, 'error_info', None)
                if not error_info:
                    exc_info = sys.exc_info()
                    #raise e.__class__, e, exc_info[2]
                    self.error_info = (e, exc_info)
                continue

        sys.path.pop(0)

    def classes(self):
        """the partial self.class_name will be used to find actual TestCase classes"""
        for module in self.modules():
            cs = inspect.getmembers(module, inspect.isclass)
            class_name = getattr(self, 'class_name', u'')
            class_regex = ''
            if class_name:
                class_regex = re.compile(ur'^{}'.format(class_name), re.I)

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
            ms = inspect.getmembers(c, inspect.ismethod)
            method_name = getattr(self, 'method_name', u'')
            method_regex = ''
            if method_name:
                if method_name.startswith(self.method_prefix):
                    method_regex = re.compile(ur'^{}'.format(method_name), re.I)

                else:
                    method_regex = re.compile(
                        ur'^{}[_]{{0,1}}{}'.format(self.method_prefix, method_name),
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
        module_name = getattr(self, 'module_name', u'')
        module_prefix = getattr(self, 'prefix', u'')
        basedir = self.basedir

        found = False
        module_regex = ''
        if module_name:
            if module_name.startswith('test') or module_name.endswith('test'):
                module_regex = re.compile(
                    ur'^{}\.py$'.format(module_name),
                    re.I
                )

            else:
                module_regex = re.compile(
                    ur'^(?:test_?{}|{}.*?_?test)\.py$'.format(module_name, module_name),
                    re.I
                )

        else:
            module_regex = re.compile(ur'^(?:test\S+|\S+test)\.py$', re.I)

        prefix_regex = ''
        if module_prefix:
            #prefix_regex = re.compile(module_prefix.replace('.', '[\\/]'), re.I)
            prefix_regex = re.compile(module_prefix, re.I)

        for root, dirs, files in os.walk(basedir, topdown=True):
            dirs[:] = [d for d in dirs if d[0] != '.'] # ignore dot directories
            if prefix_regex:
                if not prefix_regex.search(root): continue

            for f in files:
                if module_regex.search(f):
                    filepath = os.path.join(root, f)
                    found = True
                    echo.debug('module: {}', filepath)
                    yield filepath

    def module_path(self, filepath):
        """given a filepath like /base/path/to/module.py this will convert it to
        path.to.module so it can be imported"""
        basedir = self.basedir
        module_name = filepath.replace(basedir, u'', 1)
        module_name = module_name.strip('\\/')

        # remove all dirs that don't have an __init__.py file (ie, they're not modules)
        modules = re.split('[\\/]', module_name)
        module_count = len(modules)
        if module_count > 1:
            for x in xrange(module_count):
                path_args = [basedir]
                path_args.extend(modules[0:x + 1])
                path_args.append(u'__init__.py')
                module_init = os.path.join(*path_args)
                if os.path.isfile(module_init): break

            if x > 1:
                echo.debug(
                    'Removed {} from {} because is is not a python module',
                    os.sep.join(modules[0:x]), module_name
                )

            module_name = u'.'.join(modules[x:])

        # convert the remaining file path to a python module path that can be imported
        module_name = re.sub(ur'.py$', u'', module_name, flags=re.I)
        return module_name


class TestLoader(unittest.TestLoader):
    """
    https://docs.python.org/2/library/unittest.html#unittest.TestLoader
    """
    def __init__(self, basedir):
        super(TestLoader, self).__init__()
        self.basedir = self.normalize_dir(basedir)

    def normalize_dir(self, d):
        '''
        get rid of things like ~/ and ./ on a directory

        d -- string
        return -- string -- d, now with 100% more absolute path
        '''
        d = os.path.expanduser(d)
        d = os.path.abspath(d)
        return d

    def loadTestsFromName(self, name, *args, **kwargs):
        ts = self.suiteClass()
        ti = TestInfo(name, self.basedir, self.testMethodPrefix)
        found = False
        for i, tc in enumerate(ti.possible, 1):
            echo.debug("{}. Searching for test matching: {}", i, tc)
            if tc.has_method():
                for c, mn in tc.method_names():
                    #echo.debug('adding test method to suite: {}', mn)
                    echo.out('Found method test: {}.{}.{}', c.__module__, c.__name__, mn)
                    found = True
                    ts.addTest(c(mn))

            elif tc.has_class():
                for c in tc.classes():
                    #echo.debug('adding testcase to suite: {}', c.__name__)
                    echo.out('Found class test: {}.{}', c.__module__, c.__name__)
                    found = True
                    ts.addTest(self.loadTestsFromTestCase(c))

            else:
                for m in tc.modules():
                    #echo.debug('adding module to suite: {}', m.__name__)
                    echo.out('Found module test: {}', m.__name__)
                    found = True
                    ts.addTest(self.loadTestsFromModule(m))

                # if we found a module that matched then don't try for method
                if found: break

        if not found:
            ti.raise_any_error()

        return ts
        #return super(TestLoader, self).loadTestsFromName(*args, **kwargs)

    def loadTestsFromNames(self, names, *args, **kwargs):
        ts = self.suiteClass()
        for name in names:
            name_suite = self.loadTestsFromName(name, *args, **kwargs)
            ts.addTest(name_suite)

        return ts
        #return super(TestLoader, self).loadTestsFromNames(*args, **kwargs)


def run_test(name, basedir, **kwargs):
    '''
    run the test found with find_test() with unittest

    **kwargs -- dict -- all other args to pass to unittest
    '''
    ret_code = 0
    tl = TestLoader(basedir)

    kwargs.setdefault('argv', ['run_test'])
    kwargs['argv'].append(name)

    #kwargs.setdefault('module', tl.module)
    kwargs.setdefault('exit', False)
    #kwargs.setdefault('failfast', True)
    kwargs.setdefault('testLoader', tl)

    # https://docs.python.org/2/library/unittest.html#unittest.main
    ret = unittest.main(**kwargs)
    if len(ret.result.errors) or len(ret.result.failures):
        ret_code = 1

    elif not ret.result.testsRun:
        ret_code = 1

    echo.debug('Test returned: {}', ret_code)
    return ret_code


