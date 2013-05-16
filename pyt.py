# -*- coding: utf-8 -*-
import argparse
import re
import os
import ast

def find_test_info(module):
    bits = module.split('.')
    possible = []
    module_class = u''
    module_method = u''
    module_prefix = u''

    # check if the last bit is a Class
    if re.search(r'[A-Z]', bits[-1]):
        possible.append({
            'class': bits[-1],
            'module': bits[-2] if len(bits) > 1 else u'',
            'prefix': os.sep.join(bits[0:-2])
        })
    elif len(bits) > 2 and re.search(r'[A-Z]', bits[-2]):
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

    return possible

    # check if the second to last bit is a class (eg, we have Class.method)

def get_testcase_generator(module_filename, class_name=None):
    module_src = open(module_filename, 'rU').read()
    module_tree = ast.parse(module_src, module_filename)
    for module_node in module_tree.body:
        if isinstance(module_node, ast.ClassDef):
            if re.search(ur'TestCase$', module_node.name):
                if not class_name or (class_name == module_node.name):
                    yield module_node

def get_testmethod_generator(class_node, method_name=None):
    for child_node in class_node:
        if isinstance(child_node, ast.FunctionDef):
            if re.search(ur'^test_', child_node.name):
                if not method_name or (method_name == child_node.name):
                    yield child_node

def get_testmodule_generator(basedir):
    for root, dirs, files in os.walk(basedir):
        for f in files:
            if re.search(ur'^(?:test\S+|\S+test)\.py$', f, re.I):
                filepath = os.path.join(root, f)
                yield filepath

def get_test(basedir, filepath, class_name=None):
    module = filepath.replace(basedir, u'')
    module = re.sub(ur'.py$', u'', module, flags=re.I)
    module = re.sub(ur'^{sep}|{sep}$'.format(sep=os.sep), u'', module)
    module = module.replace(os.sep, u'.')
    if class_name:
        module += u'.{}'.format(class_name)
    return module


def find_test_module(test_info, basedir):
    basedir = os.path.expanduser(basedir)
    basedir = os.path.abspath(basedir)

    test_module = test_info.get('module', u'')

    test_class = test_info.get('class', u'')
    if test_class:
        test_class = u'{}TestCase'.format(test_class)

    test_method = test_info.get('method', u'')
    if test_method:
        test_method = u'test_{}'.format(test_method)

    try:
        if test_module:
            for filepath in get_testmodule_generator(basedir):
                for ast_class in get_testcase_generator(filepath, test_class):
            for root, dirs, files in os.walk(basedir):
                # if has module, if not, then we just need to find every test file and look for class/method
                for format_str in [u'test{}', u'test_{}', u'{}test', u'{}_test']:
                    test_module_name = format_str.format(test_module)
                    test_module_filename = os.path.join(
                        root,
                        test_info.get('prefix', u''),
                        u'{}.py'.format(test_module_name)
                    )
                    if os.path.isfile(test_module_filename):
                        test_module = []

                        root_prefix = root.replace(basedir, u'')
                        root_prefix = re.sub(ur'^{sep}|{sep}$'.format(sep=os.sep), u'', root_prefix)
                        root_prefix = root_prefix.replace(os.sep, u'.')
                        test_module.append(root_prefix)

                        test_module.append(test_info.get('prefix', u'').replace(os.sep, u'.'))
                        test_module.append(test_module_name)
                        if test_class:
                            test_module.append(test_class)
                            test_module.append(test_method)

                        elif test_method:
                            try:
                                test_module_src = open(test_module_filename, 'rU').read()
                                # we need to find the test class
                                test_module_tree = ast.parse(test_module_src, test_module_filename)
                                for test_module_node in test_module_tree.body:
                                    if isinstance(test_module_node, ast.ClassDef):
                                        if re.search(ur'TestCase$', test_module_node.name):
                                            for test_class_node in test_module_node.body:
                                                if test_method == test_class_node.name:
                                                    test_module.append(test_module_node.name) # class
                                                    test_module.append(test_method)
                                                    raise StopIteration()

                                raise LookupError(u"Could not find a TestCase with {} method".format(test_method))

                            except StopIteration:
                                pass

                        test_module = u'.'.join(filter(None, test_module))
                        raise StopIteration()

            raise LookupError(u"Could not find a test module for {}".format(test_info['module']))

        else:
            for filepath in get_testmodule_generator(basedir):
                for ast_class in get_testcase_generator(filepath, test_class):
                    test_module = get_test(basedir, filepath, ast_class.name)
                    raise StopIteration()

    except StopIteration:
        pass

        return test_module

if __name__ == u'__main__':
    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description='Easy Python Testing')
    parser.add_argument('modules', metavar='MODULE', nargs='+', help='modules you want to test')
    parser.add_argument('--basedir', dest='basedir', default=os.curdir, help='base directory, defaults to current working directory')

    args = parser.parse_args()

    for module in args.modules:
        tests_info = find_test_info(module)
        for test_info in tests_info:
            try:
                test_module = find_test_module(test_info, args.basedir)
                if test_module:
                    pout.v(test_module)
                    exit()
            except LookupError, e:
                pout.v(e)
                pass
        
