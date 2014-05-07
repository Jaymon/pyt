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

from . import echo


class TestInfo(object):
    @property
    def suite(self):
        self.set_possible()
        ts = unittest.TestSuite()
        for i, tc in enumerate(self.possible, 1):
            echo.debug("{}. Searching for test matching: {}", i, tc)
            ts.addTest(tc.suite)

        return ts

    def __init__(self, name, basedir, **kwargs):
        self.name = name
        self.basedir = basedir

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

        # check if the last bit is a Class
        if re.search(ur'^[A-Z]', bits[-1]):
            echo.debug('Found class in name: {}', bits[-1])
            possible.append(TestCaseInfo(basedir, **{
                'class_name': bits[-1],
                'module_name': bits[-2] if len(bits) > 1 else u'',
                'prefix': os.sep.join(bits[0:-2])
            }))
        elif len(bits) > 1 and re.search(ur'^[A-Z]', bits[-2]):
            echo.debug('Found class in name: {}', bits[-2])
            possible.append(TestCaseInfo(basedir, **{
                'class_name': bits[-2],
                'method_name': bits[-1],
                'module_name': bits[-3] if len(bits) > 2 else u'',
                'prefix': os.sep.join(bits[0:-3])
            }))
        else:
            if self.name:
                echo.debug('name is ambiguous')
                possible.append(TestCaseInfo(basedir, **{
                    'module_name': bits[-1],
                    'prefix': os.sep.join(bits[0:-1])
                }))
                possible.append(TestCaseInfo(basedir, **{
                    'method_name': bits[-1],
                    'module_name': bits[-2] if len(bits) > 1 else u'',
                    'prefix': os.sep.join(bits[0:-2])
                }))

            else:
                possible.append(TestCaseInfo(basedir))

        self.possible = possible


class TestCaseInfo(object):

    method_prefix = 'test'

    @property
    def suite(self):
        ts = unittest.TestSuite()
#        class_name = getattr(self, 'class_name', u'')
#        method_name = getattr(self, 'method_name', u'')
        for c, mn in self.method_names():
            echo.debug('adding test to suite: {}', mn)
            ts.addTest(c(mn))

        return ts

    def __init__(self, basedir, **kwargs):
        self.basedir = basedir
        for k, v in kwargs.iteritems():
            setattr(self, k, v)

    def __str__(self):
        ret = u''
        for k in ['prefix', 'module_name', 'class_name', 'method_name']:
            v = getattr(self, k, None)
            if v:
                ret += u"{}: {}, ".format(k, v)

        return ret.rstrip(', ')

    def modules(self):
        """return modules that match module_name"""
        module_name = getattr(self, 'module_name', u'TestCaseInfo_modules')
        for p in self.paths():
            # http://stackoverflow.com/questions/67631/
            m = imp.load_source(module_name, p)
            yield m

    def classes(self):
        """the partial self.class_name will be used to find actual TestCase classes"""
        for module in self.modules():
            cs = inspect.getmembers(module, inspect.isclass)
            class_name = getattr(self, 'class_name', u'')

            for c_name, c in cs:
                can_yield = True
                if class_name and class_name not in c_name:
                    can_yield = False

                if can_yield and issubclass(c, unittest.TestCase):
                    if c is not unittest.TestCase:
                        echo.debug('class: {}', c_name)
                        yield c

    def method_names(self):
        """return the actual test methods that matched self.method_name"""
        for c in self.classes():
            ms = inspect.getmembers(c, inspect.ismethod)
            method_name = getattr(self, 'method_name', u'')

            for m_name, m in ms:
                if not m_name.startswith(self.method_prefix): continue

                can_yield = True
                if method_name and method_name not in m_name:
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
                    can_yield = True
                    if module_name and module_name not in f:
                        can_yield = False

                    if can_yield:
                        filepath = os.path.join(root, f)
                        found = True
                        echo.debug('module: {}', filepath)
                        yield filepath

        if not found:
            raise LookupError(
                u'No test module for basedir: "{}", module_name: "{}", module_prefix: "{}"'.format(
                    basedir,
                    module_name,
                    module_prefix
                )
            )

    def module_path(self, filepath):
        # TODO -- I don't think this works or does anything useful
        module_name = filepath.replace(self.basedir, u'', 1)
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
        ti = TestInfo(name, self.basedir)
        return ti.suite
        #return super(TestLoader, self).loadTestsFromName(*args, **kwargs)

    def loadTestsFromNames(self, names, *args, **kwargs):
        ts = unittest.TestSuite()
        for name in names:
            name_suite = self.loadTestsFromName(name, *args, **kwargs)
            ts.addTest(name_suite)

        return ts
        #return super(TestLoader, self).loadTestsFromNames(*args, **kwargs)

    def loadTestsFromTestCase(self, *args, **kwargs):
        echo.debug('load from test case')
        ti = TestInfo('', self.basedir)
        return ti.suite
        #return super(TestLoader, self).loadTestsFromTestCase(*args, **kwargs)

    def loadTestsFromModule(self, *args, **kwargs):
        echo.debug('load from module')
        ti = TestInfo('', self.basedir)
        return ti.suite
        #return super(TestLoader, self).loadTestsFromModule(*args, **kwargs)

    def getTestCaseNames(self, *args, **kwargs):
        echo.debug('get test case names')
        ti = TestInfo('', self.basedir)
        return ti.suite
        #return super(TestLoader, self).getTestCaseNames(*args, **kwargs)

    def discover(self, *args, **kwargs):
        echo.debug('discover')
        ti = TestInfo('', self.basedir)
        return ti.suite
        #return super(TestLoader, self).discover(*args, **kwargs)


def run_test(name, basedir, **kwargs):
    '''
    run the test found with find_test() with unittest

    test -- Test -- the found test
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

    #echo.out("Test: {}", test)
    try:
        ret = unittest.main(**kwargs)
        if len(ret.result.errors) or len(ret.result.failures):
            ret_code = 1

    except LookupError, e:
        echo.debug(e)
        ret_code = 1

    echo.debug('Test returned: {}', ret_code)
    return ret_code


