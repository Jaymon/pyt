# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import unittest
from unittest import TestCase
import os
import sys
import subprocess

import testdata

# remove any global pyt
# NOTE -- when I actually got rid of the modules (just the .pop() without the
# reassignment to bak.) it caused all kinds of strange and subtle issues, but
# only when I was running the tests with a global pyt
for k in list(sys.modules.keys()):
    if k.startswith("pyt.") or k == "pyt":
        sys.modules["bak.{}".format(k)] = sys.modules.pop(k)


import pyt
from pyt import tester
from pyt import echo
from pyt.compat import *


echo.DEBUG = True
testdata.basic_logging()


# from testdata.client import ModuleCommand
# 
# class Client(ModuleCommand):
#     def __init__(self, basedir=""):
#         super(Client, self).__init__("pyt", cwd=basedir)
# 

class Client(object):
    """makes running a captain script nice and easy for easy testing"""
    def __init__(self, cwd):
        self.cwd = cwd

    def run(self, arg_str='', **options):
        #cmd = "python -m pyt --basedir={} {}".format(self.cwd, arg_str)
        cmd = "{} -m pyt --basedir={} {}".format(sys.executable, self.cwd, arg_str)
        expected_ret_code = options.get('code', 0)

        def get_output_str(output):
            if is_py2:
                return "\n".join(output)
            elif is_py3:
                return "\n".join((o.decode("utf-8") for o in output))

        output = []
        try:
            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=os.curdir
            )

            for line in iter(process.stdout.readline, b""):
                output.append(line.rstrip())

            process.wait()
            if process.returncode != expected_ret_code:
                raise RuntimeError("cmd returned {} with output: {}".format(
                    process.returncode,
                    get_output_str(output)
                ))

        except subprocess.CalledProcessError as e:
            raise RuntimeError("cmd returned {} with output: {}".format(e.returncode, e.output))

        return get_output_str(output)


class TestModule(object):
    @property
    def client(self):
        return Client(self.cwd)

    @property
    def test(self):
        t = tester.Test()
        t.module_name = self.name
        return t

    @property
    def tl(self):
        tl = tester.TestLoader(self.cwd, tester.TestEnviron())
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
            self.name = "prefix{}.pmod{}_test".format(
                testdata.get_ascii(5),
                testdata.get_ascii(5)
            )

        bits = self.name.rsplit('.', 1)
        self.module_name = bits[1] if len(bits) == 2 else bits[0]
        self.prefix = bits[0] if len(bits) == 2 else ''
        self.name_prefix = bits[1][:4] if len(bits) == 2 else bits[0][:4]

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
    def test_filename(self):
        ti = tester.TestInfo("foo/bar/che.py", '/tmp')
        self.assertEqual("/tmp/foo/bar/che.py", list(ti.possible[0].paths())[0])

        ti = tester.TestInfo("/foo/bar/che.py", '/tmp')
        self.assertEqual("/foo/bar/che.py", list(ti.possible[0].paths())[0])

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
            for i, to in enumerate(test_out):
                for k, v in to.items():
                    r = getattr(ti.possible[i], k)
                    self.assertEqual(v, r)

    def test_no_name(self):
        ti = tester.TestInfo('', '/tmp')
        self.assertEqual(1, len(ti.possible))


class RunTestTest(TestCase):
    def test_double_counting_and_pyc(self):
        """Make sure packages don't get double counted"""
        # https://github.com/Jaymon/pyt/issues/18
        # https://github.com/Jaymon/pyt/issues/19
        basedir = testdata.create_modules({
            "dc_test": "",
            "dc_test.bar_test": [
                "from unittest import TestCase",
                "class BarTest(TestCase):",
                "   def test_baz(self): pass",
            ],
            "dc_test.che_test": [
                "from unittest import TestCase",
                "class CheTest(TestCase):",
                "   def test_baz(self): pass",
            ]
        })

        s = Client(basedir)
        r = s.run("dc_test --debug")
        self.assertTrue("Found 2 total tests" in r)

        # running it again will test for the pyc problem
        r = s.run("dc_test --debug")
        self.assertFalse("No module named pyc" in r)

        r = s.run("--all --debug")
        self.assertTrue("Found 2 total tests" in r)

        r = s.run("--all --debug")
        self.assertFalse("No module named pyc" in r)

    def test_all(self):
        m = TestModule(
            "from __future__ import print_function",
            "from unittest import TestCase",
            "",
            "class BarTest(TestCase):",
            "    def test_bar(self):",
            "        print('in bar test')",
            "",
        )

        s = Client(m.cwd)
        r = s.run("--all") # should buffer
        r2 = s.run("") # should print "in bar test"
        r3 = s.run("--buffer") # should be just like --all
        self.assertNotEqual(r, r2)
        self.assertEqual(r, r3)

    def test_multiple(self):
        basedir = testdata.create_modules({
            "multiple_test": "",
            "multiple_test.bar_test": [
                "from unittest import TestCase",
                "class BarTest(TestCase):",
                "   def test_baz(self): pass",
            ],
            "multiple_test.che_test": [
                "from unittest import TestCase",
                "class CheTest(TestCase):",
                "   def test_baz(self): pass",
            ]
        })

        s = Client(basedir)
        r = s.run("bar che --debug")
        self.assertTrue("bar_test" in r)
        self.assertTrue("che_test" in r)
        self.assertEqual(2, r.count("Ran 1 test"))

    def test_buffer(self):
        m = TestModule(
            "from __future__ import print_function",
            "from unittest import TestCase",
            "",
            "class BarTest(TestCase):",
            "    def test_bar(self):",
            "        print('in bar test')",
            "",
        )

        s = Client(m.cwd)
        r = s.run("pmod --buffer")
        self.assertFalse("in bar test" in r)

        r = s.run("pmod.Bar.bar")
        self.assertTrue("in bar test" in r)

        r = s.run("pmod.Bar.bar --buffer")
        self.assertFalse("in bar test" in r)

        r = s.run("pmod.Bar --buffer")
        self.assertFalse("in bar test" in r)

        r = s.run("pmod.Bar")
        self.assertTrue("in bar test" in r)

    def test_filepath(self):
        m = testdata.create_module("bar.foo_test", [
            "from unittest import TestCase",
            "class FooTest(TestCase):",
            "    def test_foo(self):",
            "        pass",
            "",
        ])

        s = Client(m.basedir)
        s.run("{}".format(m.module.__file__))
        s.run("{}:Foo".format(m.module.__file__))
        s.run("{}:Foo.foo".format(m.module.__file__))
        with self.assertRaises(RuntimeError):
            s.run("{}:Bah".format(m.module.__file__))

    def test_package(self):
        m = testdata.create_package("foo_test", [
            "from __future__ import print_function",
            "from unittest import TestCase",
            "class FooTest(TestCase):",
            "    def test_foo(self):",
            "        print('in foo test')",
            "",
        ])

        s = Client(m.basedir)
        r = s.run("foo_test")
        self.assertTrue("in foo test" in r)

    def test_environ(self):
        m = TestModule(
            "import os",
            "from unittest import TestCase",
            "",
            "class BarTest(TestCase):",
            "    def test_bar(self):",
            "        if int(os.environ['PYT_TEST_COUNT']) == 1:",
            "            raise ValueError('test count 1')",
            "",
            "class FooTest(TestCase):",
            "    def test_foo(self):",
            "        if int(os.environ['PYT_TEST_COUNT']) == 2:",
            "            raise ValueError('test count 2')",
            "",
            "    def test_che(self):",
            "        pass",
        )

        s = Client(m.cwd)

        with self.assertRaises(RuntimeError):
            r = s.run('Bar --debug')

        with self.assertRaises(RuntimeError):
            r = s.run('Foo --debug')

        r = s.run('pmod --debug')

    def test_debug(self):
        m = TestModule(
            "from __future__ import print_function",
            "from unittest import TestCase",
            "",
            "class DebugTest(TestCase):",
            "  def test_debug(self):",
            "    print('hi')",
            "",
            name="debug_test"
        )

        s = Client(m.cwd)

        r = s.run('debug_test --buffer --debug')
        r2 = s.run('debug_test --debug')
        r3 = s.run('debug_test --buffer')
        self.assertNotEqual(r, r2)
        self.assertNotEqual(r, r3)
        self.assertNotEqual(r2, r3)

    def test_parse_error2(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class ParseErrorTest(TestCase):",
            "  count = 5",
            "  return",
            "",
            name="parse_error2_test"
        )

        s = Client(m.cwd)

        with self.assertRaises(RuntimeError):
            r = s.run('parse_error2_test')

    def test_testcase_not_found(self):
        """ https://github.com/Jaymon/pyt/issues/1 """
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class BARTest(TestCase):",
            "  def test_che(self): pass"
            "",
            name="foo_test"
        )

        s = Client(m.cwd)

        r = s.run('foo_test.BARTest.test_che --debug')
        self.assertTrue('foo_test.BARTest.test_che' in r)

    def test_error_print_on_failure(self):
        """tests weren't printing errors even on total failure, this makes sure
        that's fixed"""
        m = TestModule(
            "from unittest import TestCase",
            "import something_that_does_not_exist"
            "",
        )

        s = Client(m.cwd)

        r = s.run('--all', code=1)
        self.assertTrue(len(r) > 0)

    def test_failfast_1(self):
        m = TestModule([
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
        ])

        s = Client(m.cwd)

        r = s.run('--all --failfast', code=1)
        self.assertTrue('.F.' not in r)

        r = s.run('--all', code=1)
        self.assertTrue('.F.' in r)

    def test_failfast_2(self):
        m = TestModule([
            "from __future__ import print_function",
            "from unittest import TestCase",
            "",
            "class BarTest(TestCase):",
            "    def test_1bar(self):",
            "        print('in bar test')",
            "        self.assertTrue(False)",
            "    def test_2foo(self):",
            "        print('in foo test')",
        ])

        s = m.client
        r = s.run("-fb", code=1)
        self.assertTrue("FAIL: test_1bar" in r)
        self.assertTrue("Ran 1 test" in r)

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
                'ritests': 'from unittest import TestCase',
                'ritests.foo_test': "\n".join([
                    'from . import TestCase',
                    '',
                    'class FooTest(TestCase):',
                    '    def test_bar(self): pass'
                ])
            },
            tmpdir=cwd
        )

        ret_code = tester.run_test('Foo.bar', cwd)

    def test_multi(self):
        # if there is an error in one of the tests but another test is found, don't
        # bubble up the error
        cwd = testdata.create_dir()
        testdata.create_modules(
            {
                'multi.bar_test': "\n".join([
                    'from unittest import TestCase',
                    '',
                    'class BarTest(TestCase):',
                    '    def test_bar(self): pass',
                ]),
                'multi.foo_test': "\n".join([
                    'from unittest import TestCase',
                    '',
                    'class FooTest(TestCase):',
                    '    def test_foo(self): pass',
                    '',
                    'class CheTest(TestCase):',
                    '    def test_che(self): pass',
                ])
            },
            tmpdir=cwd
        )

        ret_code = tester.run_test('multi.', cwd)
        self.assertEqual(0, ret_code)

    def test_no_tests_found(self):
        # if there is an error in one of the tests but another test is found, don't
        # bubble up the error
        cwd = testdata.create_dir()
        testdata.create_modules(
            {
                'nofound.nofo_test': "\n".join([
                    'from unittest import TestCase',
                    '',
                    'class NofoTest(TestCase):',
                    '    def test_nofo(self): pass',
                ]),
            },
            tmpdir=cwd
        )

        ret_code = tester.run_test('nofound_does_not_exist.', cwd)
        self.assertEqual(1, ret_code)

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

        ret_code = tester.run_test('cli_2.', cwd)
        self.assertEqual(0, ret_code)

        # if there is an error and no other test is found, bubble up the error
        m = TestModule(
            "from unittest import TestCase",
            "",
            "raise ValueError('foo')"
        )

        with self.assertRaises(ValueError):
            ret_code = tester.run_test(m.name_prefix, m.cwd)

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

    def test_prefix_search2(self):
        m = TestModule(
            "from unittest import TestCase",
            "",
            "class FooBarTest(TestCase):",
            "    def test_blah(self):",
            "        pass",
            name='ps2.foobar.chebaz_test'
        )

        s = Client(m.cwd)
        ret_code = tester.run_test('foobar.', m.cwd)
        self.assertEqual(0, ret_code)

        ret_code = tester.run_test('ps2.', m.cwd)
        self.assertEqual(0, ret_code)

    def test_setup(self):
        m = TestModule(
            "from __future__ import print_function",
            "from unittest import TestCase",
            "",
            "def setUpModule():",
            "    print('here')",
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

    def test_names_1(self):
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

    def test_names_2(self):
        m = TestModule([
            "from __future__ import print_function",
            "from unittest import TestCase",
            "",
            "class Names2Test(TestCase):",
            "    def test_1name(self):",
            "        print('test 1')",
            "",
            "    def test_2name(self):",
            "        print('test 2')",
        ])

        s = m.client
        r = s.run("Names2.1name Names2.2name")
        self.assertEqual(2, r.count("Ran 1 test"))


class TestLoaderTest(TestCase):
    def test_private_testcase(self):
        # https://github.com/Jaymon/pyt/issues/17
        m = TestModule(
            "from unittest import TestCase as BaseTC",
            "",
            "class _TestCase(BaseTC):",
            "   def test_common(self): pass",
            "",
            "class CheTest(_TestCase):",
            "   def test_foo(self): pass"
        )

        tl = m.tl
        s = tl.loadTestsFromName(m.name)
        r = str(s)
        self.assertFalse("_TestCase.test_common" in r)

        s = tl.loadTestsFromName("{}.Che".format(m.name))
        r = str(s)
        self.assertFalse("_TestCase.test_common" in r)

        s = tl.loadTestsFromName("{}.Che.foo".format(m.name))
        r = str(s)
        self.assertFalse("_TestCase.test_common" in r)

    def test_package_1(self):
        basedir = testdata.create_modules({
            "packagefoo2_test": "",
            "packagefoo2_test.bar_test": [
                "from unittest import TestCase",
                "class BarTest(TestCase):",
                "   def test_baz(self): pass",
            ],
            "packagefoo2_test.che_test": [
                "from unittest import TestCase",
                "class CheTest(TestCase):",
                "   def test_baz(self): pass",
            ]
        })

        tl = tester.TestLoader(basedir, tester.TestEnviron())
        s = tl.loadTestsFromName("packagefoo")
        self.assertTrue('BarTest' in str(s))
        self.assertTrue('CheTest' in str(s))

        basedir = testdata.create_modules({
            "packagefoo_test": "",
            "packagefoo_test.bar": "",
            "packagefoo_test.bar.zoom_test": [
                "from unittest import TestCase",
                "class BarTest(TestCase):",
                "   def test_baz(self): pass",
            ],
            "packagefoo_test.che_test": [
                "from unittest import TestCase",
                "class CheTest(TestCase):",
                "   def test_baz(self): pass",
            ]
        })

        tl = tester.TestLoader(basedir, tester.TestEnviron())
        s = tl.loadTestsFromName("packagefoo")
        self.assertTrue('BarTest' in str(s))
        self.assertTrue('CheTest' in str(s))

        basedir = testdata.create_modules({
            "tests": "",
            "tests.bar_test": [
                "from unittest import TestCase",
                "class BarTest(TestCase):",
                "   def test_baz(self): pass",
            ],
            "tests.che_test": [
                "from unittest import TestCase",
                "class CheTest(TestCase):",
                "   def test_baz(self): pass",
            ]
        })

        tl = tester.TestLoader(basedir, tester.TestEnviron())
        s = tl.loadTestsFromName("tests")
        self.assertTrue('BarTest' in str(s))
        self.assertTrue('CheTest' in str(s))

    def test_package_2(self):
        """https://github.com/Jaymon/pyt/issues/23"""
        basedir = testdata.create_modules({
            "p2tests.foo.bar.baz_test": [
                "from unittest import TestCase",
                "class BazTest(TestCase):",
                "   def test_foo(self): pass",
            ],
            "p2tests.foo.bar.boo_test": [
                "from unittest import TestCase",
                "class BooTest(TestCase):",
                "   def test_foo(self): pass",
            ],
            "p2tests.foo.bar.che_test": [
                "from unittest import TestCase",
                "class CheTest(TestCase):",
                "   def test_foo(self): pass",
            ],
        })

        tl = tester.TestLoader(basedir, tester.TestEnviron())
        s = tl.loadTestsFromName("foo.bar")
        self.assertTrue('BazTest' in str(s))
        self.assertTrue('BooTest' in str(s))
        self.assertTrue('CheTest' in str(s))

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
            "from __future__ import print_function",
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
            "       print('bar')",
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


# import threading
# class ThreadingTest(TestCase):
# 
#     def test_threading_import(self):
#         """Turns out there is a race condition when importing common.models.chat,
#         this test is the minimum viable fail case so Jay can track it down"""
#         saved_chat = sys.modules.pop("testdata", None)
# 
#         def target():
#             import testdata
# 
#         #t1 = TestThread(target=target)
#         t1 = threading.Thread(target=target)
#         t1.start()
#         t1.join()
# 


