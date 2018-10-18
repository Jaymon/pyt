# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import sys

import testdata

from pyt.tester import TestProgram
from pyt import __version__
from . import TestCase, TestModule


class TestProgramTest(TestCase):
    def test_version(self):
        m = TestModule([
            "class VersionTest(TestCase):",
            "    def test_one(self):",
            "        pass",
        ])

        r = m.client.run("--version")
        self.assertTrue(sys.executable in r)
        self.assertTrue(__version__ in r)

    def test_single_run(self):
        m = TestModule(
            "class SingleRunTest(TestCase):",
            "    def test_bar(self): pass",
        )

        r = m.client.run(m.name)
        self.assertTrue("Ran 1 test" in r)

    def test_multi_run(self):
        m = TestModule(
            "class MultiRunTest(TestCase):",
            "    def test_foo(self): pass",
            "    def test_bar(self): pass",
        )

        r = m.client.run("MultiRun.foo MultiRun.bar")
        self.assertTrue("Ran 2 tests" in r)

    def test_blank_run(self):
        m = TestModule({
            "blank1_test": [
                "class OneTest(TestCase):",
                "    def test_one(self):",
                "        pass",
                "",
            ],
            "blank2_test": [
                "class TwoTest(TestCase):",
                "    def test_two(self):",
                "        pass",
                "",
            ],
        })

        r = m.client.run()
        self.assertTrue("Ran 2 tests" in r)

    def test_buffer_1(self):
        m = TestModule(
            "class BarTest(TestCase):",
            "    def test_bar(self):",
            "        print('in bar test')",
            "",
        )
        s = m.client

        r = s.run("--buffer pmod")
        self.assertFalse("in bar test" in r)

        r = s.run("pmod.Bar.bar")
        self.assertTrue("in bar test" in r)

        r = s.run("--buffer pmod.Bar.bar")
        self.assertFalse("in bar test" in r)

        r = s.run("--buffer pmod.Bar")
        self.assertFalse("in bar test" in r)

        r = s.run("pmod.Bar")
        self.assertTrue("in bar test" in r)

    def test_buffer_2(self):
        buffered_s = testdata.get_ascii_words()
        m = TestModule(
            "class BufferTest(TestCase):",
            "    def test_bar(self):",
            "        print('{}')".format(buffered_s),
        )

        r = m.client.run("--verbose Buffer.bar")
        self.assertTrue(buffered_s in r)
        self.assertTrue("Guessing test name:" in r)

        r = m.client.run("Buffer.bar")
        self.assertFalse("Guessing test name:" in r)
        self.assertTrue(buffered_s in r)

        pout.b()
        r = m.client.run("--buffer Buffer.bar")
        self.assertFalse("Guessing test name:" in r)
        self.assertFalse(buffered_s in r)

        r = m.client.run("--buffer --verbose Buffer.bar")
        self.assertTrue("Guessing test name:" in r)
        self.assertFalse(buffered_s in r)

    def test_buffer_3(self):
        m = TestModule(
            "class DebugTest(TestCase):",
            "  def test_debug(self):",
            "    print('hi')",
            "",
        )
        s = m.client

        r = s.run('--buffer --verbose {}'.format(m.name))
        r2 = s.run('--verbose {}'.format(m.name))
        r3 = s.run('--buffer {}'.format(m.name))
        self.assertNotEqual(r, r2)
        self.assertNotEqual(r, r3)
        self.assertNotEqual(r2, r3)


    def test_multi_cli(self):
        m = TestModule({
            "multicli_test": [
                "class OneTest(TestCase):",
                "    def test_one(self):",
                "        pass",
                "",
            ],
            "climulti_test": [
                "class TwoTest(TestCase):",
                "    def test_two(self):",
                "        pass",
                "",
            ],
        })

        r = m.client.run("multicli.One.one climulti.Two.two")
        self.assertTrue("Ran 2 tests" in r)

    def test_multiple(self):
        m = TestModule({
            "multiple_test": "",
            "multiple_test.bar_test": [
                "class BarTest(TestCase):",
                "   def test_baz(self): pass",
            ],
            "multiple_test.che_test": [
                "class CheTest(TestCase):",
                "   def test_baz(self): pass",
            ]
        })

        s = m.client
        r = s.run("--verbose bar che")
        self.assertTrue("bar_test" in r)
        self.assertTrue("che_test" in r)
        self.assertEqual(2, r.count("Found 1 total tests"))

    def test_double_counting_and_pyc(self):
        """Make sure packages don't get double counted"""
        # https://github.com/Jaymon/pyt/issues/18
        # https://github.com/Jaymon/pyt/issues/19
        m = TestModule({
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

        s = m.client
        s.environ["PYTHONDONTWRITEBYTECODE"] = "0"

        r = s.run("dc_test")
        self.assertTrue("Ran 2 tests" in r)

        # running it again will test for the pyc problem
        r = s.run("--verbose dc_test")
        self.assertFalse("No module named pyc" in r)

        r = s.run("--verbose")
        self.assertTrue("Found 2 total tests" in r)
        self.assertFalse("No module named pyc" in r)

    def test_filepath(self):
        m = TestModule([
            "class FooTest(TestCase):",
            "    def test_foo(self):",
            "        pass",
        ])
        s = m.client

        r = s.run("--verbose {}:Bah".format(m.path))
        self.assertTrue("Ran 0 tests" in r)

        r = s.run("--verbose {}".format(m.path))
        self.assertTrue("Ran 1 test" in r)

        r = s.run("{}:Foo".format(m.path))
        self.assertTrue("Ran 1 test" in r)

        r = s.run("{}:Foo.foo".format(m.path))
        self.assertTrue("Ran 1 test" in r)

    def test_package(self):
        m = TestModule([
            "class FooTest(TestCase):",
            "    def test_foo(self):",
            "        print('in foo test')",
            "",
        ], package=True)

        s = m.client
        r = s.run("--verbose {}".format(m.name))
        self.assertTrue("in foo test" in r)

    def test_skip_tests(self):
        """https://github.com/Jaymon/pyt/issues/27"""
        m = TestModule(
            "class SkipTTest(TestCase):",
            "    @classmethod",
            "    def setUpClass(cls):",
            "        pyt.skip_multi_class()",
            "",
            "    def test_bar(self): pass",
        )
        c = m.client
        r = c.run('--verbose SkipT.bar')
        self.assertTrue("Ran 1 test" in r)

    def test_parse_error_1(self):
        m = TestModule({
            'tests_parse_error': 'from unittest import TestCase',
            'tests_parse_error.pefoo_test': [
                'from . import TestCase',
                '',
                'class PEFooTest(TestCase):',
                '    def test_bar(self):',
                '        foo = "this is a parse error'
            ]
        })
        s = m.client

        with self.assertRaises(RuntimeError):
            ret_code = s.run('PEFoo.bar')

    def test_parse_error_2(self):
        m = TestModule(
            "class ParseErrorTest(TestCase):",
            "  count = 5",
            "  return", # a return not in a method?
        )
        s = m.client

        with self.assertRaises(RuntimeError):
            r = s.run(m.name)

    def test_testcase_not_found(self):
        """ https://github.com/Jaymon/pyt/issues/1 """
        m = TestModule(
            "class BARTest(TestCase):",
            "  def test_che(self): pass"
            "",
        )
        s = m.client

        r = s.run('--verbose {}.BARTest.test_che'.format(m.name))
        self.assertTrue('test_che ({}.BARTest)'.format(m.name) in r)

    def test_error_print_on_failure(self):
        """tests weren't printing errors even on total failure, this makes sure
        that's fixed"""
        m = TestModule(
            "import something_that_does_not_exist"
        )
        s = m.client

        r = s.run('', code=1)
        self.assertTrue(len(r) > 0)

    def test_failfast_1(self):
        m = TestModule([
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
        s = m.client

        r = s.run('--failfast', code=1)
        self.assertTrue('.F.' not in r)

        r = s.run('', code=1)
        self.assertTrue('.F.' in r)

    def test_failfast_2(self):
        m = TestModule([
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

    def test_relative_import(self):
        m = TestModule({
            'ritests': 'from unittest import TestCase',
            'ritests.foo_test': "\n".join([
                'from . import TestCase',
                '',
                'class FooTest(TestCase):',
                '    def test_bar(self): pass'
            ])
        })
        s = m.client
        r = s.run("Foo.bar")
        self.assertTrue("Ran 1 test" in r)

    def test_cli_errors(self):
        m = TestModule({
            'cli_errors': 'from unittest import TestCase',
            'cli_errors.clibar_test': [
                'from . import TestCase',
                '',
                "raise ValueError('foo')"
            ],
            'cli_errors.foo_test': [
                'from . import TestCase',
                '',
                'class CliFooTest(TestCase):',
                '    def test_bar(self): pass',
            ]
        })
        s = m.client

        r = s.run("cli_errors.")
        self.assertTrue("Ran 1 test" in r)

        # if there is an error and no other test is found, bubble up the error
        m = TestModule(
            "from unittest import TestCase",
            "",
            "raise ValueError('foo')"
        )
        s = m.client

        with self.assertRaises(RuntimeError):
            s.run(m.name_prefix)

    def test_cli_run(self):
        m = TestModule(
            "class BarTest(TestCase):",
            "    def test_foo(self):",
            "        pass",
        )
        s = m.client

        r = s.run('--verbose {}'.format(m.name_prefix))
        self.assertTrue("Ran 1 test")

        r = s.run('--verbose blah.blarg.blorg')
        self.assertTrue("Ran 0 tests")

    def test_found_module_ignore_method(self):
        m = TestModule(
            "class FooTest(TestCase):",
            "    def test_foo(self):",
            "        pass",
        )
        s = m.client

        r = s.run('--verbose foo')
        self.assertTrue('Found method test: {}'.format(m.name) in r)

    def test_ignore_non_test_modules(self):
        """make sure similar named non-test modules are ignored"""
        m = TestModule({
            'tintm.tint_test': "\n".join([
                "class FooTest(TestCase):",
                "    def test_foo(self):",
                "        pass",

            ]),
            'tintm.tint': ""
        })
        s = m.client

        r = s.run('--verbose tint')
        self.assertEqual(1, r.count('Found module test'))

    def test_prefix_search_1(self):
        m = TestModule(
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
        s = m.client

        r = s.run('--verbose {}.*Bar'.format(m.name))
        self.assertTrue("Ran 3 tests" in r)

        r = s.run('--verbose Bar.*handshake')
        self.assertTrue('test_bad_accept_handshake' in r)
        self.assertTrue('test_handshake' in r)

        r = s.run('--verbose test_handshake')
        self.assertTrue('Found method test: prefix_search.chebaz_test.BarTest.test_handshake' in r)

        r = s.run('--verbose Bar.test_handshake')
        self.assertTrue('Found method test: prefix_search.chebaz_test.BarTest.test_handshake' in r)

        r = s.run('--verbose che')
        self.assertTrue('Found module test: prefix_search.chebaz_test' in r)

        r = s.run('--verbose baz')
        self.assertTrue('Ran 0 tests' in r)

        r = s.run('Bar.handshake --debug')
        self.assertTrue('bad_accept_handshake' not in r)

        r = s.run('Bar --debug')
        self.assertTrue('FooBarTest' not in r)

    def test_prefix_search_2(self):
        m = TestModule(
            "class FooBarTest(TestCase):",
            "    def test_blah(self):",
            "        pass",
            name='ps2.foobar.chebaz_test'
        )
        s = m.client

        r = s.run('foobar.')
        self.assertTrue("Ran 1 test" in r)

        r = s.run('ps2.')
        self.assertTrue("Ran 1 test" in r)

    def test_testcase_parent(self):
        m = TestModule(
            "class BaseTCase(TestCase):",
            "    def test_foo(self):",
            "        pass",
            "",
            "class BarTest(BaseTCase):",
            "    pass"
        )
        s = m.client

        r = s.run("--verbose {}".format(m.name_prefix))
        self.assertTrue("Ran 2 tests" in r)

    def test_setup(self):
        m = TestModule(
            "def setUpModule():",
            "    print('*setUpModule*')",
            "",
            "def tearDownModule():",
            "    print('*tearDownModule*')",
            "",
            "class SetupCase(TestCase):",
            "    @classmethod",
            "    def setUpClass(cls):",
            "         print('*setUpClass*')",
            "",
            "    def setUp(self):",
            "         print('*setUp*')",
            "",
            "    def tearDown(self):",
            "         print('*tearDown*')",
            "",
            "    @classmethod",
            "    def tearDownClass(cls):",
            "         print('*tearDownClass*')",
            "",
            "    def test_foo(self):",
            "        pass",
        )
        s = m.client

        r = s.run(m.name_prefix)
        calls = [
            "*setUpModule*",
            "*tearDownModule*",
            "*setUpClass*",
            "*tearDownClass*",
            "*setUp*",
            "*tearDown*"
        ]
        for call in calls:
            self.assertTrue(call in r)

    def test_names_1(self):
        m = TestModule(
            "class BaseTCase(TestCase):",
            "   def test_foo(self):",
            "       pass",
            "",
            "class BarTest(BaseTCase):",
            "   pass"
        )
        s = m.client

        ret_code = s.run(m.name_prefix)
        self.assertTrue("Ran 2 tests")

        ret_code = s.run("")
        self.assertTrue("Ran 2 tests")

    def test_names_2(self):
        m = TestModule([
            "class Names2Test(TestCase):",
            "    def test_1name(self):",
            "        print('test 1')",
            "",
            "    def test_2name(self):",
            "        print('test 2')",
        ])
        s = m.client

        r = s.run("Names2.1name Names2.2name")
        self.assertTrue("test 1" in r)
        self.assertTrue("test 2" in r)
        self.assertTrue("Ran 2 tests")

    def test_warnings(self):
        """https://github.com/Jaymon/pyt/issues/25"""
        # !!! this worked:
        #import warnings
        #warnings.warn("blah blah blah")
        # python3 -W error -m unittest pyt_test.RunTestTest.test_warning

        m = TestModule(
            "import warnings",
            "",
            "class WarningsTest(TestCase):",
            "    def test_warning(self):",
            "        warnings.warn('this warning should be an error')",
        )
        c = m.client
        r = c.run(m.name)
        self.assertTrue("this warning should be an error" in r)

        r = c.run("{} --warnings".format(m.name), code=1)
        self.assertTrue("errors=1" in r)


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

        tl = m.loader
        s = tl.loadTestsFromName(m.name)
        r = str(s)
        self.assertTrue(r)
        self.assertFalse("_TestCase.test_common" in r)

        s = tl.loadTestsFromName("{}.Che".format(m.name))
        r = str(s)
        self.assertTrue(r)
        self.assertFalse("_TestCase.test_common" in r)

        s = tl.loadTestsFromName("{}.Che.foo".format(m.name))
        r = str(s)
        self.assertTrue(r)
        self.assertFalse("_TestCase.test_common" in r)

    def test_package_1(self):
        m = TestModule({
            "packagefoo2_test": "",
            "packagefoo2_test.bar_test": [
                "class BarTest(TestCase):",
                "   def test_baz(self): pass",
            ],
            "packagefoo2_test.che_test": [
                "class CheTest(TestCase):",
                "   def test_baz(self): pass",
            ]
        })
        tl = m.loader

        s = tl.loadTestsFromName("packagefoo")
        pout.v(str(s))
        self.assertTrue('BarTest' in str(s))
        self.assertTrue('CheTest' in str(s))

        m = TestModule({
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
        tl = m.loader

        s = tl.loadTestsFromName("packagefoo")
        self.assertTrue('BarTest' in str(s))
        self.assertTrue('CheTest' in str(s))

        # on 10-13-2018 I changed this from tests to p1tests because I think
        # there was a name conflict when running all tests which caused this to
        # fail
        m = TestModule({
            "p1tests": "",
            "p1tests.bar_test": [
                "from unittest import TestCase",
                "class BarTest(TestCase):",
                "   def test_baz(self): pass",
            ],
            "p1tests.che_test": [
                "from unittest import TestCase",
                "class CheTest(TestCase):",
                "   def test_baz2(self): pass",
            ]
        })
        tl = m.loader

        s = tl.loadTestsFromName("p1tests")
        self.assertTrue('BarTest' in str(s))
        self.assertTrue('CheTest' in str(s))

    def test_package_2(self):
        """https://github.com/Jaymon/pyt/issues/23"""
        m = TestModule({
            "p2tests.foo.bar.baz_test": [
                "class BazTest(TestCase):",
                "   def test_foo(self): pass",
            ],
            "p2tests.foo.bar.boo_test": [
                "class BooTest(TestCase):",
                "   def test_foo(self): pass",
            ],
            "p2tests.foo.bar.che_test": [
                "class CheTest(TestCase):",
                "   def test_foo(self): pass",
            ],
        })
        tl = m.loader

        s = tl.loadTestsFromName("foo.bar")
        self.assertTrue('BazTest' in str(s))
        self.assertTrue('BooTest' in str(s))
        self.assertTrue('CheTest' in str(s))

    def test_suite(self):
        m = TestModule(
            "class CheTest(TestCase):",
            "   def test_foo(self): pass"
        )
        tl = m.loader

        s = tl.loadTestsFromName(m.name)
        self.assertTrue('test_foo' in str(s))

        s = tl.loadTestsFromName('{}.Bar.foo'.format(m.name))
        self.assertFalse('test_foo' in str(s))

        s = tl.loadTestsFromName('{}.foo'.format(m.name))
        self.assertTrue('test_foo' in str(s))


# class TestResultTest(TestCase):
#     def test_buffering(self):
#         m = TestModule(
#             "from __future__ import print_function",
#             "from unittest import TestCase",
#             "import logging",
#             "import sys",
#             "",
#             "logging.basicConfig()",
#             "logger = logging.getLogger(__name__)",
#             "logger.setLevel(logging.DEBUG)",
#             "log_handler = logging.StreamHandler(stream=sys.stderr)",
#             "logger.addHandler(log_handler)",
#             "",
#             "class BaseTResultTestCase(TestCase):",
#             "   def test_success(self):",
#             "       logger.info('foo')",
#             "",
#             "   def test_failure(self):",
#             "       logger.info('foo')",
#             "       print('bar')",
#             "       self.assertTrue(False)",
#             "",
#         )
# 
#         search_str = '{}.BaseTResultTestCase.failure'.format(m.name)
#         t = tester.main(
#             search_str,
#             m.cwd,
#             buffer=True,
#         )
# 
#         search_str = '{}.BaseTResultTestCase.success'.format(m.name)
#         t = tester.main(
#             search_str,
#             m.cwd,
#             buffer=True,
#         )
# 
#         search_str = '{}.BaseTResultTestCase.success'.format(m.name)
#         t = tester.main(
#             search_str,
#             m.cwd
#         )
# 

