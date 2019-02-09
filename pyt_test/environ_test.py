# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import


from pyt.environ import TestEnviron
from . import TestCase, TestModule


class EnvironTest(TestCase):
    def test_environ_1(self):
        m = TestModule(
            "import os",
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
        s = m.client

        with self.assertRaises(RuntimeError):
            s.run('--verbose Bar')

        with self.assertRaises(RuntimeError):
            s.run('--verbose Foo')

        r = s.run('--verbose {}'.format(m.name_prefix))

    def test_environ_2(self):
        m = TestModule({
            "foo_test": [
                "def setUpModule():",
                "    counts = pyt.get_counts()",
                "    for k, n in counts.items():",
                "        print('{}: {}'.format(k, n))",
                "",
                "class FooTest(TestCase):",
                "    def test_one_class(self):",
                "        pyt.skip_multi_class('one_class')",
                "    def test_one_module(self):",
                "        pyt.skip_multi_module('one_module')",
            ],
            "bar_test": [
                "def setUpModule():",
                "    pyt.skip_multi_module('bar_module')",
                "",
                "class BarTest(TestCase):",
                "    def test_one(self):",
                "        pyt.skip_multi_test('one_test')",
                "    def test_two(self):",
                "        #print(pyt.get_counts())",
                "        pass",
                "",
            ],
        })
        c = m.client

        # running one class
        r = c.run('--verbose bar.Bar')
        self.assertTrue("test_one ({}.bar_test.BarTest)".format(m.name) in r)
        self.assertTrue("test_two ({}.bar_test.BarTest)".format(m.name) in r)
        self.assertTrue("Ran 2 tests" in r)

        # running modules
        r = c.run('--verbose {}'.format(m.name), ret_code=1)
        self.assertTrue("skipped=3" in r)

        # running one test
        #r = c.run('bar.Bar.one --debug', code=1)
        #self.assertTrue("skipped=1" in r)
        r = c.run('--verbose bar.Bar.one')
        self.assertTrue("Ran 1 test" in r)

        # running one module
        r = c.run('--verbose bar')
        self.assertTrue("test_one ({}.bar_test.BarTest)".format(m.name) in r)
        self.assertTrue("test_two ({}.bar_test.BarTest)".format(m.name) in r)
        self.assertTrue("Ran 2 tests" in r)
        self.assertTrue("skipped=1" in r)


