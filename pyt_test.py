import unittest
import os
import sys

# remove any global pyt
if 'pyt' in sys.modules:
    del sys.modules['pyt']

import pyt

def setUpModule():
    file_structure = [
        # root, dirs, files
        ('/foo', ['1', '2', 'test'], ['__init__.py']),
        ('/foo/1', [], ['__init__.py', 'one.py', 'two.PY']),
        ('/foo/2', ['3'], ['__init__.py', 'three.py', 'four.py']),
        ('/foo/2/3', [], ['__init__.py', 'five.py', 'five_test.py']),
        ('/foo/test', ['1', '2'], ['__init__.py']),
        ('/foo/test/1', [], ['__init__.py', 'one_test.py', 'testtwo.py']),
        ('/foo/test/2', [], ['__init__.py', 'threetest.py', 'test_four.py']),
    ]

    test_modules = [
        '/foo/2/3/five_test.py',
        '/foo/test/1/one_test.py',
        '/foo/test/1/testtwo.py',
        '/foo/test/2/threetest.py',
        '/foo/test/2/test_four.py',
    ]

    pyt.os.walk = lambda *a, **kw: iter(file_structure)
    pyt.os.path.isfile = lambda f: f in test_modules

class PytTest(unittest.TestCase):
    def test_find_test_info(self):
        tests = (
            ('foo.bar', [{'module': 'bar', 'prefix': 'foo'}, {'method': 'bar', 'module': 'foo', 'prefix': ''}]),
            ('foo.Bar', [{'module': 'foo', 'class': 'Bar', 'prefix': ''}]),
            ('foo.Bar.baz', [{'module': 'foo', 'class': 'Bar', 'prefix': '', 'method': 'baz'}]),
            ('prefix.foo.Bar.baz', [{'module': 'foo', 'class': 'Bar', 'prefix': 'prefix', 'method': 'baz'}]),
            ('pre.fix.foo.Bar.baz', [{'module': 'foo', 'class': 'Bar', 'prefix': 'pre/fix', 'method': 'baz'}]),
            ('Call.controller', [{'class': 'Call', 'method': 'controller', 'prefix': '', 'module': ''}]),
            ('Call', [{'class': 'Call', 'prefix': '', 'module': ''}]),
        )

        for test_in, test_out in tests:
            ret = pyt.find_test_info(test_in)
            self.assertEqual(ret, test_out)

    def test_find_test_module(self):
        tests = (
            (u'five', u'2.3.five_test'),
            (u'five_test', u'2.3.five_test'),
            (u'one', u'test.1.one_test'),
        )

        for test_in, test_out in tests:
            test = pyt.find_test({'module': test_in}, '/foo')
            self.assertEqual(test.module_name, test_out)


