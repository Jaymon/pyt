import unittest
from unittest import TestCase
import os
import sys
import subprocess

import testdata

# remove any global pyt
if 'pyt' in sys.modules:
    sys.modules['__pyt_old'] = sys.modules['pyt']
    del sys.modules['pyt']

import pyt
from pyt import tester
from pyt import echo

echo.DEBUG = True


#def setUpModule():
#    """
#    set up the test module with a file structure to test finding different modules
#
#    basically, the idea of this folder structure is that /foo will have not be a submodule (no
#    __init__.py file) but lots of other folders will be modules
#    """
#    # TODO -- switch over to use testdata instead of monkey patch
#    return
#    file_structure = [
#        # root, dirs, files
#        ('/foo', ['1', '2', 'test', 'bar', 'one'], []),
#        ('/foo/1', [], ['__init__.py', 'one.py', 'two.PY']),
#
#        ('/foo/2', ['3'], ['__init__.py', 'three.py', 'four.py']),
#        ('/foo/2/3', [], ['__init__.py', 'five.py', 'five_test.py']),
#
#        ('/foo/test', ['1', '2'], ['__init__.py']),
#        ('/foo/test/1', [], ['__init__.py', 'one_test.py', 'testtwo.py']),
#        ('/foo/test/2', [], ['__init__.py', 'threetest.py', 'test_four.py']),
#
#        ('/foo/bar', ['che'], []),
#        ('/foo/bar/che', [], ['__init__.py', 'six_test.py']),
#
#        ('/foo/one', ['two'], []),
#        ('/foo/one/two', ['three'], []),
#        ('/foo/one/two/three', [], ['__init__.py', 'seven_test.py']),
#    ]
#
#    test_modules = [
#        '/foo/2/3/five_test.py',
#        '/foo/test/1/one_test.py',
#        '/foo/test/1/testtwo.py',
#        '/foo/test/2/threetest.py',
#        '/foo/test/2/test_four.py',
#        '/foo/bar/che/six_test.py',
#        '/foo/one/two/three/seven_test.py',
#
#    ]
#
#    all_files = list(test_modules)
#    all_files.extend([
#        '/foo/1/__init__.py',
#        '/foo/2/__init__.py',
#        '/foo/2/3/__init__.py',
#        '/foo/test/__init__.py',
#        '/foo/test/1/__init__.py',
#        '/foo/test/2/__init__.py',
#        '/foo/bar/che/__init__.py',
#        '/foo/one/two/three/__init__.py',
#    ])
#
#    pyt.os.walk = lambda *a, **kw: iter(file_structure)
#    pyt.os.path.isfile = lambda f: (f in all_files)
#

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

        with self.assertRaises(AssertionError):
            a ** {'foo': 3}

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


class Client(object):
    """makes running a captain script nice and easy for easy testing"""
    def __init__(self, cwd):
        self.cwd = cwd

    def run(self, arg_str='', **options):
        cmd = "python -m pyt --basedir={} {}".format(self.cwd, arg_str)
        expected_ret_code = options.get('code', 0)

        r = ''
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.curdir
            )

            while True:
                char = process.stdout.read(1)
                if char == '' and process.poll() is not None:
                    break
                sys.stdout.write(char)
                sys.stdout.flush()
                r += char

            if process.returncode != expected_ret_code:
                raise RuntimeError("cmd returned {} with output".format(process.returncode, r))

        except subprocess.CalledProcessError, e:
            raise RuntimeError("cmd returned {} with output: {}".format(e.returncode, e.output))

        return r


class TestModule(object):
    @property
    def test(self):
        t = tester.Test()
        t.module_name = self.name
        return t

    @property
    def tl(self):
        tl = tester.TestLoader(self.cwd)
        return tl

    @property
    def tci(self):
        """return a TestCaseInfo instance for this module"""
        tc = tester.TestCaseInfo(
            self.cwd,
            module_name=self.module_name, 
            prefix=self.prefix
        )
        return tc

    def __init__(self, *body, **kwargs):
        if len(body) == 1: body = body[0]

        self.body = body
        if not isinstance(body, basestring):
            self.body = "\n".join(body)

        self.cwd = testdata.create_dir()

        name = kwargs.get('name', '')
        if name:
            self.name = name
        else:
            self.name = "prefix{}.pmod{}_test".format(testdata.get_ascii(5), testdata.get_ascii(5))

        self.module_name = self.name.rsplit('.', 1)[1]
        self.prefix = self.name.rsplit('.', 1)[0]

        self.path = testdata.create_module(
            self.name,
            self.body,
            self.cwd
        )


class TestCaseInfoTest(TestCase):

    def test_method_names(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class CheTest(TestCase):",
            "   def test_foo(self): pass",
            name="foo.bar_test"
        )

        tc = m.tci
        tc.class_name = 'Che'
        tc.method_name = 'foo'

        r = list(tc.method_names())
        self.assertEqual(1, len(r))

    def test_paths(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class CheTest(TestCase):",
            "   pass",
            name="foo.bar.baz_test"
        )

        tc = m.tci

        cs = list(tc.paths())
        self.assertEqual(1, len(cs))

        tc.prefix = 'boom.bam'
        #with self.assertRaises(LookupError):
        cs = list(tc.paths())
        self.assertEqual(0, len(cs))

    def test_classes(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class BaseTCase(TestCase):",
            "   def test_foo(self):",
            "       pass",
            "",
            "class BarTest(BaseTCase):",
            "   pass"
        )

        tc = m.tci
        cs = list(tc.classes())
        self.assertEqual(2, len(cs))

        tc.class_name = 'Bar'
        cs = list(tc.classes())
        self.assertEqual(1, len(cs))


class TestInfoTest(TestCase):
    def test_set_possible(self):
        tests = (
            ('foo.bar', [{'module_name': 'bar', 'prefix': 'foo'}, {'method_name': 'bar', 'module_name': 'foo', 'prefix': ''}]),
            ('foo.Bar', [{'module_name': 'foo', 'class_name': 'Bar', 'prefix': ''}]),
            ('foo.Bar.baz', [{'module_name': 'foo', 'class_name': 'Bar', 'prefix': '', 'method_name': 'baz'}]),
            ('prefix.foo.Bar.baz', [{'module_name': 'foo', 'class_name': 'Bar', 'prefix': 'prefix', 'method_name': 'baz'}]),
            ('pre.fix.foo.Bar.baz', [{'module_name': 'foo', 'class_name': 'Bar', 'prefix': 'pre/fix', 'method_name': 'baz'}]),
            ('Call.controller', [{'class_name': 'Call', 'method_name': 'controller', 'prefix': '', 'module_name': ''}]),
            ('Call', [{'class_name': 'Call', 'prefix': '', 'module_name': ''}]),
            ('Boom.fooBar', [{'class_name': 'Boom', 'prefix': '', 'module_name': '', 'method_name': 'fooBar'}]),
            ('get_SQL', [{'module_name': 'get_SQL', 'prefix': ''}, {'method_name': 'get_SQL', 'module_name': '', 'prefix': ''}]),
        )

        for test_in, test_out in tests:
            ti = tester.TestInfo(test_in, '/tmp')
            ti.set_possible()
            for i, to in enumerate(test_out):
                for k, v in to.iteritems():
                    r = getattr(ti.possible[i], k)
                    self.assertEqual(v, r)

    def test_no_name(self):
        ti = tester.TestInfo('', '/tmp')
        ti.set_possible()
        self.assertEqual(1, len(ti.possible))


class RunTestTest(TestCase):
    def test_failfast(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class FailFastTestCase(TestCase):",
            "   def test_aoo(self):",
            "       self.assertTrue(True)",
            "",
            "   def test_foo(self):",
            "       self.assertTrue(False)",
            "",
            "   def test_zoo(self):",
            "       self.assertTrue(True)",
        )

        s = Client(m.cwd)

        r = s.run('--all', code=1)
        self.assertTrue('.F.' not in r)

        r = s.run('--all --no-failfast', code=1)
        self.assertTrue('.F.' in r)

    def test_parse_error(self):
        cwd = testdata.create_dir()
        testdata.create_modules(
            {
                'tests_parse_error': 'from unittest import TestCase',
                'tests_parse_error.pefoo_test': "\n".join([
                    'from . import TestCase',
                    '',
                    'class PEFooTest(TestCase):',
                    '    def test_bar(self):',
                    '        foo = "this is a parse error'
                ])
            },
            tmpdir=cwd
        )

        with self.assertRaises(SyntaxError):
            ret_code = tester.run_test('PEFoo.bar', cwd)

    def test_relative_import(self):
        cwd = testdata.create_dir()
        testdata.create_modules(
            {
                'tests': 'from unittest import TestCase',
                'tests.foo_test': "\n".join([
                    'from . import TestCase',
                    '',
                    'class FooTest(TestCase):',
                    '    def test_bar(self): pass'
                ])
            },
            tmpdir=cwd
        )

        ret_code = tester.run_test('Foo.bar', cwd)

    def test_cli_errors(self):
        # if there is an error in one of the tests but another test is found, don't
        # bubble up the error
        cwd = testdata.create_dir()
        testdata.create_modules(
            {
                'cli_2': 'from unittest import TestCase',
                'cli_2.clibar_test': "\n".join([
                    'from . import TestCase',
                    '',
                    "raise ValueError('foo')"
                ]),
                'cli_2.clifoo_test': "\n".join([
                    'from . import TestCase',
                    '',
                    'class CliFooTest(TestCase):',
                    '    def test_bar(self): pass',
                ])
            },
            tmpdir=cwd
        )

        ret_code = tester.run_test('clifoo', cwd)
        self.assertEqual(0, ret_code)

        # if there is an error and no other test is found, bubble up the error
        m = TestModule(
            "from unittest import TestCase",
            "",
            "raise ValueError('foo')"
        )

        with self.assertRaises(ValueError):
            ret_code = tester.run_test('pmod', m.cwd)

    def test_cli(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class BarTest(TestCase):",
            "    def test_foo(self):",
            "        pass",
        )

        s = Client(m.cwd)
        r = s.run('pmod --debug')

        with self.assertRaises(RuntimeError):
            r = s.run('blah.blarg.blorg --debug')
        #self.assertEqual(0, ret_code)

    def test_found_module_ignore_method(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class FooTest(TestCase):",
            "    def test_foo(self):",
            "        pass",
            name='prefix_search.foo_test'
        )

        s = Client(m.cwd)

        r = s.run('foo --debug')
        self.assertTrue('Found module test: prefix_search.foo_test' in r)
        self.assertTrue('test_foo' not in r)

    def test_ignore_non_test_modules(self):
        """make sure similar named non-test modules are ignored"""
        cwd = testdata.create_dir()
        testdata.create_modules(
            {
                'tintm.tint_test': "\n".join([
                    "from unittest import TestCase",
                    "",
                    "class FooTest(TestCase):",
                    "    def test_foo(self):",
                    "        pass",

                ]),
                'tintm.tint': ""
            },
            tmpdir=cwd
        )

        s = Client(cwd)
        r = s.run('tint --debug')
        self.assertEqual(1, r.count('Found module test'))

    def test_prefix_search(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class BarTest(TestCase):",
            "    def test_handshake(self):",
            "        pass",
            "    def test_bad_accept_handshake(self):",
            "        pass",
            "",
            "class FooBarTest(TestCase):",
            "    def test_blah(self):",
            "        pass",
            name='prefix_search.chebaz_test'
        )

        s = Client(m.cwd)

        r = s.run('test_handshake --debug')
        self.assertTrue('Found method test: prefix_search.chebaz_test.BarTest.test_handshake' in r)

        r = s.run('Bar.test_handshake --debug')
        self.assertTrue('Found method test: prefix_search.chebaz_test.BarTest.test_handshake' in r)

        r = s.run('che --debug')
        self.assertTrue('Found module test: prefix_search.chebaz_test' in r)

        with self.assertRaises(RuntimeError):
            r = s.run('baz --debug')

        # maybe add this sometime in the future
        #r = s.run('Bar.*handshake --debug')
        #pout.v(r)
        #self.assertTrue('bad_accept_handshake' not in r)

        r = s.run('Bar.handshake --debug')
        self.assertTrue('bad_accept_handshake' not in r)

        r = s.run('Bar --debug')
        self.assertTrue('FooBarTest' not in r)

    def test_setup(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "def setUpModule():",
            "    print 'here'",
            "",
            "class BaseTCase(TestCase):",
            "    def test_foo(self):",
            "        pass",
            "",
            "class BarTest(BaseTCase):",
            "    pass"
        )

        ret_code = tester.run_test('pmod', m.cwd)
        self.assertEqual(0, ret_code)

    def test_names(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class BaseTCase(TestCase):",
            "   def test_foo(self):",
            "       pass",
            "",
            "class BarTest(BaseTCase):",
            "   pass"
        )

        ret_code = tester.run_test('pmod', m.cwd)
        self.assertEqual(0, ret_code)

        ret_code = tester.run_test('', m.cwd)
        self.assertEqual(0, ret_code)


class TestLoaderTest(TestCase):
    def test_suite(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class CheTest(TestCase):",
            "   def test_foo(self): pass"
        )

        tl = m.tl
        s = tl.loadTestsFromName(m.name)
        self.assertTrue('test_foo' in str(s))

        s = tl.loadTestsFromName('{}.Bar.foo'.format(m.name))
        self.assertFalse('test_foo' in str(s))

        s = tl.loadTestsFromName('{}.foo'.format(m.name))
        self.assertTrue('test_foo' in str(s))

    def test_names(self):
        return
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class BaseTCase(TestCase):",
            "   def test_foo(self):",
            "       pass",
            "",
            "class BarTest(BaseTCase):",
            "   pass"
        )

        # this should call load from name(s)
        #tl = tester.TestLoader('pmod', m.cwd)
        ret_code = tester.run_test('pmod', m.cwd)

    def test_module(self):
        return
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class BaseTCase(TestCase):",
            "   def test_foo(self):",
            "       pass",
            "",
            "class BarTest(BaseTCase):",
            "   pass"
        )

        tl = tester.TestLoader('pmod', m.cwd)
        pout.v(tl.module)


    def test_getting_test(self):
        return
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class BaseTCase(TestCase):",
            "   def test_foo(self):",
            "       pass",
            "",
            "class BarTest(BaseTCase):",
            "   pass"
        )

        pout.b()
        search_str = '{}.Bar.foo'.format(m.name)
        t = tester.get_test(m.cwd, m.path, 'Bar', 'foo')
        pout.v(t)
        pout.b()


    def test_find_test_module(self):
        # TODO -- update to use testdata
        return
        tests = (
            (u'five', u'2.3.five_test'),
            (u'five_test', u'2.3.five_test'),
            (u'one', u'test.1.one_test'),
        )

        for test_in, test_out in tests:
            test = pyt.find_test({'module': test_in}, '/foo')
            self.assertEqual(test.module_name, test_out)

    def test_get_test(self):
        # TODO -- update to use testdata
        return
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


class TestResultTest(TestCase):
    def test_buffering(self):
        m = TestModule(
            "from unittest import TestCase",
            "import logging",
            "import sys",
            "",
            "logging.basicConfig()",
            "logger = logging.getLogger(__name__)",
            "logger.setLevel(logging.DEBUG)",
            "log_handler = logging.StreamHandler(stream=sys.stderr)",
            "logger.addHandler(log_handler)",
            "",
            "class BaseTResultTestCase(TestCase):",
            "   def test_success(self):",
            "       logger.info('foo')",
            "",
            "   def test_failure(self):",
            "       logger.info('foo')",
            "       print 'bar'",
            "       self.assertTrue(False)",
            "",
        )

        search_str = '{}.BaseTResultTestCase.failure'.format(m.name)
        t = tester.run_test(
            search_str,
            m.cwd,
            buffer=True,
        )

        search_str = '{}.BaseTResultTestCase.success'.format(m.name)
        t = tester.run_test(
            search_str,
            m.cwd,
            buffer=True,
        )

        search_str = '{}.BaseTResultTestCase.success'.format(m.name)
        t = tester.run_test(
            search_str,
            m.cwd
        )

