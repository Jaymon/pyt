import unittest
import os
import sys

# remove any global pyt
if 'pyt' in sys.modules:
    del sys.modules['pyt']

import pyt

def setUpModule():
    """
    set up the test module with a file structure to test finding different modules

    basically, the idea of this folder structure is that /foo will have not be a submodule (no
    __init__.py file) but lots of other folders will be modules
    """
    file_structure = [
        # root, dirs, files
        ('/foo', ['1', '2', 'test', 'bar', 'one'], []),
        ('/foo/1', [], ['__init__.py', 'one.py', 'two.PY']),

        ('/foo/2', ['3'], ['__init__.py', 'three.py', 'four.py']),
        ('/foo/2/3', [], ['__init__.py', 'five.py', 'five_test.py']),

        ('/foo/test', ['1', '2'], ['__init__.py']),
        ('/foo/test/1', [], ['__init__.py', 'one_test.py', 'testtwo.py']),
        ('/foo/test/2', [], ['__init__.py', 'threetest.py', 'test_four.py']),

        ('/foo/bar', ['che'], []),
        ('/foo/bar/che', [], ['__init__.py', 'six_test.py']),

        ('/foo/one', ['two'], []),
        ('/foo/one/two', ['three'], []),
        ('/foo/one/two/three', [], ['__init__.py', 'seven_test.py']),
    ]

    test_modules = [
        '/foo/2/3/five_test.py',
        '/foo/test/1/one_test.py',
        '/foo/test/1/testtwo.py',
        '/foo/test/2/threetest.py',
        '/foo/test/2/test_four.py',
        '/foo/bar/che/six_test.py',
        '/foo/one/two/three/seven_test.py',

    ]

    all_files = list(test_modules)
    all_files.extend([
        '/foo/1/__init__.py',
        '/foo/2/__init__.py',
        '/foo/2/3/__init__.py',
        '/foo/test/__init__.py',
        '/foo/test/1/__init__.py',
        '/foo/test/2/__init__.py',
        '/foo/bar/che/__init__.py',
        '/foo/one/two/three/__init__.py',
    ])

    pyt.os.walk = lambda *a, **kw: iter(file_structure)
    pyt.os.path.isfile = lambda f: (f in all_files)

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

    def test_get_test(self):
        #pyt.debug = True

        basedir = "/foo"
        filepath = "/foo/boom/bang/bam_test.py"
        test = pyt.get_test(basedir, filepath)
        self.assertEqual('bam_test', str(test))

        basedir = "/foo"
        filepath = "/foo/2/3/five_test.py"
        test = pyt.get_test(basedir, filepath)
        self.assertEqual('2.3.five_test', str(test))
        
        basedir = "/foo"
        filepath = "/bar/che/six_test.py"
        test = pyt.get_test(basedir, filepath)
        self.assertEqual('che.six_test', str(test))

        basedir = "/foo"
        filepath = "/one/two/three/seven_test.py"
        test = pyt.get_test(basedir, filepath)
        self.assertEqual('three.seven_test', str(test))
