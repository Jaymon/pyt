import unittest
import os
import sys

# remove any global pyt
if 'pyt' in sys.modules:
    sys.modules['__pyt_old'] = sys.modules['pyt']
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

class AssertTest(unittest.TestCase):
    def test_assertEqual(self):
        a = pyt.Assert(5)
        with self.assertRaises(AssertionError):
            a == 4

        with self.assertRaises(AssertionError):
            a == "5"

        a == 5

    def test_assertNotEqual(self):
        a = pyt.Assert(5)
        a != 4
        a != "5"

        with self.assertRaises(AssertionError):
            a != 5

    def test_greater_less_equal(self):
        a = pyt.Assert(5)
        a <= 20
        a < 20
        with self.assertRaises(AssertionError):
            a < 1

        with self.assertRaises(AssertionError):
            a <= 1

        a >= 1
        a > 1
        with self.assertRaises(AssertionError):
            a > 20

        with self.assertRaises(AssertionError):
            a >= 20

    def test_greater_zero(self):
        a = pyt.Assert(5)
        +a

        a = pyt.Assert(0)
        with self.assertRaises(AssertionError):
            +a

    def test_RegexpMatches(self):
        a = pyt.Assert("foo bar")
        a / "^f+o+"
        with self.assertRaises(AssertionError):
            a / "^[fr]+o{3}"

    def test_NotRegexpMatches(self):
        a = pyt.Assert("foo bar")
        a // "^[fr]+o{3}"
        with self.assertRaises(AssertionError):
            a // "^f+o+"

# I changed this so you can only catch exceptions with the with handler, using __call__
# will allow methods to be called from assert the same way attributes are wrapped
#    def test_assertRaises(self):
#        def boom(*args, **kwargs):
#            raise ValueError('checking')
#
#        a = pyt.Assert(boom)
#        a(ValueError)
#        self.assertIsInstance(a.exception, ValueError)

    def test_with_assertRaises(self):
        a = pyt.Assert(ValueError)
        with a:
            raise ValueError('checking')

        self.assertIsInstance(a.exception, ValueError)

    def test_assertIsInstance(self):
        a = pyt.Assert(1)
        a % int
        with self.assertRaises(AssertionError):
            a % str

        a = pyt.Assert(range(5))
        a % (list, tuple)

    def test_keys_in(self):
        a = pyt.Assert(range(5))
        a * (1, 2, 3)
        a *  1
        with self.assertRaises(AssertionError):
            a * (1, 5, 6)

        a = pyt.Assert({'foo': 1, 'bar': 2})
        a * ('foo', 'bar')
        a * 'foo'
        with self.assertRaises(AssertionError):
            a * 'che'

        class Foo(object): pass
        f = Foo()
        f.foo = 1
        f.bar = 2
        a = pyt.Assert(f)
        a * ('foo', 'bar')
        a * 'foo'
        with self.assertRaises(AssertionError) as cm:
            a * 'che'

    def test_keys_only_in(self):
        a = pyt.Assert(range(5))
        a *= (0, 1, 2, 3, 4)
        with self.assertRaises(AssertionError):
            a *= (0, 1, 2)

        a = pyt.Assert({'foo': 1, 'bar': 2})
        a *= ('foo', 'bar')
        with self.assertRaises(AssertionError):
            a *= 'foo'

    def test_keys_vals_in(self):
        d = {'foo': 1, 'bar': 2}
        a = pyt.Assert(d)
        a ** d
        with self.assertRaises(AssertionError):
            a ** {'che': 3}

        class Foo(object): pass
        f = Foo()
        f.foo = 1
        f.bar = 2
        a = pyt.Assert(f)
        a ** d
        with self.assertRaises(AssertionError):
            a ** {'che': 3}

    def test_keys_vals_only_in(self):
        d = {'foo': 1, 'bar': 2}
        a = pyt.Assert(d)
        a **= d
        with self.assertRaises(AssertionError):
            a **= {'foo': 1}

    def test_assertNotIsInstance(self):
        a = pyt.Assert(1)
        a ^ str
        with self.assertRaises(AssertionError):
            a ^ int

    def test_getattr(self):
        class Che(object): pass
        o = Che()
        o.foo = 1
        o.bar = "this is a string"

        a = pyt.Assert(o)
        a.foo == 1
        with self.assertRaises(AssertionError) as cm:
            a.foo == 2

        a.bar == "this is a string"
        with self.assertRaises(AssertionError) as cm:
            a.bar == "this is not a string"

    def test_getitem(self):
        d = {'foo': 1}
        a = pyt.Assert(d)

        a['foo'] == 1
        with self.assertRaises(AssertionError) as cm:
            a['foo'] == 2

        with self.assertRaises(KeyError) as cm:
            a['bar']

        a = pyt.Assert(1)
        with self.assertRaises(TypeError) as cm:
            a['bar']

    def test_in(self):
        l = range(5)
        a = pyt.Assert(l)
        3 in a
        with self.assertRaises(AssertionError) as cm:
            3 not in a

        with self.assertRaises(AssertionError) as cm:
            20 in a

    def test_bool(self):
        a = pyt.Assert(1)
        a == True
        with self.assertRaises(AssertionError) as cm:
            a == False

        a = pyt.Assert(0)
        a == False
        with self.assertRaises(AssertionError) as cm:
            a == True

    def test_len(self):
        l = range(5)
        a = pyt.Assert(l)

        with self.assertRaises(AssertionError) as cm:
            a.len == 8

        a.len == 5
        a.len < 20
        a.len > 1
        a.len <= 20
        a.len >= 1

        with self.assertRaises(AssertionError) as cm:
            a.len >= 8

        with self.assertRaises(AssertionError) as cm:
            a.len <= 1

    def test_method(self):
        class Foo(object):
            def bar(self, val):
                return val

        f = Foo()
        a = pyt.Assert(f)
        a.bar(1) == 1

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
            ('Boom.fooBar', [{'class': 'Boom', 'prefix': '', 'module': '', 'method': 'fooBar'}]),
            ('get_SQL', [{'module': 'get_SQL', 'prefix': ''}, {'method': 'get_SQL', 'module': '', 'prefix': ''}]),
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
