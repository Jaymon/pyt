# -*- coding: utf-8 -*-
import argparse
import re
import os
import ast
import unittest
import sys

__version__ = '0.5.3'

debug = False

def console_out(format_str, *args, **kwargs):
    sys.stderr.write(format_str.format(*args, **kwargs)) 
    sys.stderr.write(os.linesep)

def console_debug(*args, **kwargs):
    if debug:
        console_out(*args, **kwargs)

class Test(object):
    '''
    an instance is created and returned in get_test() and holds all the found test info needed to run the test
    '''
    def module(self):
        '''
        just the module part of a test
        '''
        return getattr(self, 'module_name', u'')

    def specific(self):
        '''
        the class.method part of a test
        '''
        bits = (getattr(self, 'class_name', u''), getattr(self, 'method_name', u''))
        return u'.'.join(filter(None, bits))
        
    def full(self):
        '''
        the full test: module.class.method
        '''
        bits = (self.module(), self.specific())
        return u'.'.join(filter(None, bits))

    def __str__(self):
        return self.full().encode('utf-8')

def find_test_info(module):
    '''
    break up a module path to its various parts (prefix, module, class, method)

    module -- string -- the module path (module.path.Class.method)

    return -- list -- a list of possible interpretations of the module path (eg, foo.bar can be bar module in foo, or bar
                                                                             method in foo)
    '''
    bits = module.split(u'.')
    possible = []
    module_class = u''
    module_method = u''
    module_prefix = u''

    # check if the last bit is a Class
    if re.search(ur'[A-Z]', bits[-1]):
        possible.append({
            'class': bits[-1],
            'module': bits[-2] if len(bits) > 1 else u'',
            'prefix': os.sep.join(bits[0:-2])
        })
    elif len(bits) > 1 and re.search(ur'[A-Z]', bits[-2]):
        possible.append({
            'class': bits[-2],
            'method': bits[-1],
            'module': bits[-3] if len(bits) > 2 else u'',
            'prefix': os.sep.join(bits[0:-3])
        })
    else:
        possible.append({
            'module': bits[-1],
            'prefix': os.sep.join(bits[0:-1])
        })
        possible.append({
            'method': bits[-1],
            'module': bits[-2] if len(bits) > 1 else u'',
            'prefix': os.sep.join(bits[0:-2])
        })

    if debug:
        for i, p in enumerate(possible, 1):
            console_debug("{}. Searching for test matching: ", i)
            for n in ['prefix', 'module', 'class', 'method']:
                v = p.get(n, None)
                if v: console_debug("\t{}: {}", n, v)

    return possible

def get_testcase_generator(module_filename, class_name=u''):
    '''
    given a module python filename, this will yield all the test classes in the module

    module_filename -- string -- a full path to a .py file
    class_name -- string -- if specified, only test classes containing class_name are returned

    return -- generator
    '''
    regex = re.compile(ur'Test$|TestCase$')
    module_src = open(module_filename, 'rU').read()
    module_tree = ast.parse(module_src, module_filename)
    for module_node in module_tree.body:
        if isinstance(module_node, ast.ClassDef):
            if regex.search(module_node.name):
                if not class_name or (class_name in module_node.name):
                    console_debug('class: {}', module_node.name)
                    yield module_node

def get_testmethod_generator(class_node, method_name=u''):
    '''
    given an abstract class tree node, yield all the test methods in the class

    class_node -- ast.ClassDef -- the abstract class tree
    method_name -- string -- if specified, only yield methods containing method_name

    return -- generator
    '''
    regex = re.compile(ur'^test_')
    for child_node in class_node.body:
        if isinstance(child_node, ast.FunctionDef):
            if regex.search(child_node.name):
                if not method_name or re.search(ur'{}$'.format(method_name), child_node.name):
                    console_debug('method: {}', child_node.name)
                    yield child_node

def normalize_testmodule_filename(root, module_name, module_prefix=u''):
    '''
    given a module and a prefix, generate all the filenames that the test module for 
    module can be

    root -- string -- root/module_prefix/module_name
    module_name -- string
    module_prefix -- string
    return -- generator -- the full filepaths of the possible module
    '''
    basename_fmts = []
    if u'test' in module_name and not module_name == u'test':
        # we want to be transparent here with python -m unittest, so if the
        # person is passing in module_test.test_method, we want that to work
        # the same as module.method
        basename_fmts = [u'{}']
    else:
        basename_fmts = [u'test{}', u'test_{}', u'{}test', u'{}_test']

    for basename_fmt in basename_fmts:
        module_basename = basename_fmt.format(module_name)
        module_filename = os.path.join(
            root,
            module_prefix,
            u'{}.py'.format(module_basename)
        )
        yield module_filename

def get_testmodule_generator(basedir, module_name=u'', module_prefix=u''):
    '''
    given a basedir, yield all modules recursively found in basedir that are test modules

    basedir -- string -- the path to recursively check
    module_name -- string -- if specified, only return modules matching module_name
    module_prefix -- string -- if specified, only return test modules with the prefix, basically, if basedir=foo,
        module_name=bar, and modul_prefix=che.baz then a test module would have to be in bar.che.baz to be valid

    return -- generator
    '''
    found = False
    regex = re.compile(ur'^(?:test\S+|\S+test)\.py$', re.I)
    for root, dirs, files in os.walk(basedir, topdown=True):
        dirs[:] = [d for d in dirs if d[0] != '.'] # ignore dot directories
        if module_name:
            for module_filename in normalize_testmodule_filename(root, module_name, module_prefix):
                if os.path.isfile(module_filename):
                    found = True
                    console_debug('module: {}', module_filename)
                    yield module_filename

        else:
            for f in files:
                if regex.search(f):
                    filepath = os.path.join(root, f)
                    found = True
                    console_debug('module: {}', filepath)
                    yield filepath

    if not found:
        raise LookupError(u'No test module for basedir: "{}", module_name: "{}", module_prefix: "{}"'.format(
            basedir,
            module_name,
            module_prefix
        ))

def get_test(basedir, filepath, class_name=u'', method_name=u''):
    '''
    combine all the passed in arguments into a valid python module import string

    basedir -- string -- the base directory to use
    filepath -- string -- the test module full file path
    class_name -- string -- a class name
    method_name -- string -- a method name

    return -- Test() -- a Test instance with all the needed info to run the test
    '''
    test = Test()

    module_name = filepath.replace(basedir, u'', 1)
    module_name = re.sub(ur'^{sep}|{sep}$'.format(sep=os.sep), u'', module_name)

    # remove all dirs that don't have an __init__.py file (ie, they're not modules)
    modules = module_name.split(os.sep)
    module_count = len(modules)
    if module_count > 1:
        for x in xrange(module_count):
            path_args = [basedir]
            path_args.extend(modules[0:x + 1])
            path_args.append(u'__init__.py')
            module_init = os.path.join(*path_args)
            if os.path.isfile(module_init): break

        if x > 1: console_debug('Removed {} from {} because is is not a python module', os.sep.join(modules[0:x]), module_name)
        module_name = u'.'.join(modules[x:])

    # convert the remaining file path to a python module path that can be imported
    module_name = re.sub(ur'.py$', u'', module_name, flags=re.I)
    test.module_name = module_name

    if class_name:
        found = False
        for ast_class in get_testcase_generator(filepath, class_name):
            found = True
            test.class_name = ast_class.name
            if method_name:
                found = False
                for ast_method in get_testmethod_generator(ast_class, method_name):
                    found = True
                    test.method_name = ast_method.name

            if found: break

        if not found:
            raise LookupError(u"could not find a test for class {} or method {}".format(class_name, method_name))

    elif method_name:
        found = False
        for ast_class in get_testcase_generator(filepath):
            for ast_method in get_testmethod_generator(ast_class, method_name):
                found = True
                test.class_name = ast_class.name
                test.method_name = ast_method.name

            if found: break

        if not found:
            raise LookupError(u"could not find a test for method: {}".format(method_name))

    return test

def find_test(test_info, basedir):
    '''
    given some test_info returned from find_test_info(), convert that to a valid test you could
    pass to a unit tester

    test_info -- dict -- test info
    basedir -- string -- the working directory to use

    return -- Test() -- see get_test()
    '''
    test = None
    module_name = test_info.get('module', u'')
    class_name = test_info.get('class', u'')
    method_name = test_info.get('method', u'')
    module_prefix = test_info.get('prefix', u'')

    for filepath in get_testmodule_generator(basedir, module_name, module_prefix):
        try:
            test = get_test(basedir, filepath, class_name, method_name)
            break
        except LookupError:
            test = None

    return test

def run_test(test, **kwargs):
    '''
    run the test found with find_test() with unittest

    test -- Test -- the found test
    **kwargs -- dict -- all other args to pass to unittest
    '''
    ret_code = 0

    kwargs.setdefault('argv', [])
    kwargs.setdefault('module', test.module())
    kwargs.setdefault('exit', False)

    specific = test.specific()
    if specific:
        kwargs['argv'].append(specific)

    console_out("Test: {}", test)
    ret = unittest.main(**kwargs)
    if len(ret.result.errors) or len(ret.result.failures):
        ret_code = 1

    console_debug('Test returned: {}', ret_code)
    return ret_code

def normalize_dir(d):
    '''
    get rid of things like ~/ and ./ on a directory

    d -- string
    return -- string -- d, now with 100% more absolute path
    '''
    d = os.path.expanduser(d)
    d = os.path.abspath(d)
    return d

def console():
    '''
    cli hook

    return -- integer -- the exit code
    '''
    parser = argparse.ArgumentParser(description='Easy Python Testing')
    parser.add_argument('modules', metavar='TEST', nargs='+', help='the test(s) you want to run')
    parser.add_argument('--basedir', dest='basedir', default=os.curdir, help='base directory, defaults to current working directory')
    parser.add_argument('--debug', dest='debug', action='store_true', help='print debugging info')
    parser.add_argument("-v", "--version", action='version', version="%(prog)s {}".format(__version__))

    args, test_args = parser.parse_known_args()

    global debug
    debug = args.debug

    # we want to strip current working directory here and add basedir to the pythonpath
    curdir = normalize_dir(os.curdir)
    basedir = normalize_dir(args.basedir)

    # remove current dir paths because basedir will be the dir the code should think it is executing in
    for p in ['', curdir, os.curdir, '{}{}'.format(os.curdir, os.sep)]:
        if p in sys.path:
            sys.path.remove(p)

    sys.path.insert(0, basedir)
    test_args.insert(0, sys.argv[0])
    ret_code = 0

    console_debug('basedir: {}', basedir)

    for module in args.modules:
        found = False
        module = module.decode('utf-8')
        tests_info = find_test_info(module)
        for test_info in tests_info:
            try:
                test = find_test(test_info, basedir)
                if test:
                    found = True
                    ret_code |= run_test(test, argv=test_args)
                    break # only run the first test found for each passed in arg

            except LookupError, e:
                pass
        
        if not found:
            console_out("No test was found for: {}", module)
            ret_code |= 1

    return ret_code

if __name__ == u'__main__':
    sys.exit(console())

