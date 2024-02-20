# -*- coding: utf-8 -*-
import os
import inspect

import testdata

from pyt.path import PathFinder, PathGuesser, RerunFile, SitePackagesDir
from . import TestCase, TestModule


class PathFinderTest(TestCase):
    def test_issue_33(self):
        """https://github.com/Jaymon/pyt/issues/33"""
        m = TestModule({
            "foo.__init__": [
                "class Bar(object): pass",
            ],
            "foo_test": [
                "from unittest import TestCase",
                "class BarTest(TestCase):",
                "    def test_che(self): pass",
            ]
        }, name="")

        pf = m.pathfinder
        r = pf._find_module_path(m.basedir, "foo")
        self.assertTrue(r.endswith("foo_test.py"))

    def test_pyc_issues(self):
        """https://github.com/Jaymon/pyt/issues/34"""
        m = TestModule(
            "from unittest import TestCase",
            "class FooTest(TestCase):",
            "    def test_bar(self): pass",
        )

        pyc_f = testdata.create_file(
            "", 
            "{}.pyc".format(m.module.name),
            tmpdir=m.module.parent.directory
        )

        tl = m.loader
        s = tl.loadTestsFromName("{}.Foo".format(m.module_name))
        self.assertEqual(1, len(s._tests[0]._tests))
        self.assertTrue(
            inspect.getsourcefile(
                s._tests[0]._tests[0].__class__
            ).endswith(".py")
        )

    def test_issue_29(self):
        """make sure private directories are ignored

        https://github.com/Jaymon/pyt/issues/29"""
        m = TestModule({
            "issuetwentynine.__foo__.bar_test": [
                "class BarTest(TestCase):",
                "    def test_che(self): pass",
            ],
            "issuetwentynine_test._private.bar_test": [
                "class BarTest(TestCase):",
                "    def test_che(self): pass",
            ],
        }, name="")

        pf = m.pathfinder
        r = list(pf.paths())
        self.assertEqual(1, len(r))

    def test_filter_system_dirs(self):
        """if you have a virtual environment that isn't hidden or private that's
        in the current directory then pyt will happily crawl all the way through
        it looking for tests, I've put in some code to filter out the system dir
        but this might not be enough and I will have to modify it"""
        m = TestModule([
            "class BarTest(TestCase):",
            "    def test_che(self): pass",
        ])

        system_d = SitePackagesDir()
        parent_d = os.path.dirname(system_d)
        pf = m.pathfinder
        r_system = list(pf.walk(system_d))
        r_parent = list(pf.walk(m.cwd))
        # if system directories weren't filtered there would be more directories
        # in r_parent than r_system
        self.assertLess(len(r_parent), len(r_system))

    def test__find_prefix_paths(self):
        modpath = testdata.create_module(modpath="find.prefix.paths.whew_test")
        pf = PathFinder(basedir=modpath.basedir)
        r = list(pf._find_prefix_paths(pf.basedir, "find.paths"))
        self.assertEqual(1, len(r))

        basedir = testdata.create_dir()
        other_basedir = testdata.create_dir("other/directory", basedir)
        other_modpath = testdata.create_module(
            modpath="tests.fpp_test",
            tmpdir=other_basedir
        )
        modpath = testdata.create_module(
            modpath="tests.fpp_test",
            tmpdir=basedir
        )

        pf = PathFinder(basedir=basedir)
        r = list(pf._find_prefix_paths(basedir, "tests"))
        self.assertEqual(2, len(r))

    def test_glob(self):
        modpath = testdata.create_module(
            [
                "from unittest import TestCase",
                "",
                "class GlobFooTest(TestCase):",
                "    def test_bar(self):",
                "        pass",
            ],
            modpath="globbartests.globfoo_test",
        )
        pf = PathFinder(
            basedir=modpath.basedir,
            prefix="*bar",
            module_name="*foo"
        )
        r = list(pf.paths())
        self.assertEqual(1, len(r))

        r = pf._find_basename("*bar", ["globbartests"], is_prefix=True)
        self.assertEqual("globbartests", r)

        r = pf._find_basename("*bar", ["globbartests"], is_prefix=False)
        self.assertEqual("globbartests", r)

        r = pf._find_basename(
            "*foo",
            ["globfoo_test.py", "__init__.py"],
            is_prefix=False
        )
        self.assertEqual("globfoo_test.py", r)

        r = pf._find_basename(
            "*foo",
            ["globfoo_test.py", "__init__.py"],
            is_prefix=True
        )
        self.assertEqual("globfoo_test.py", r)

        pf = PathFinder(
            basedir=modpath.basedir,
            prefix="bar",
            module_name="foo"
        )
        r = list(pf.paths())
        self.assertEqual(0, len(r))

    def test__find_basename(self):
        pf = PathFinder(basedir="/does/not/matter")
        r = pf._find_basename("foo", ["foo2_test"])
        self.assertEqual("foo2_test", r)

        r = pf._find_basename("foo2", ["foo2_test"])
        self.assertEqual("foo2_test", r)

        r = pf._find_basename("fo", ["foo2_test.py", "bar_test.py"])
        self.assertEqual("foo2_test.py", r)

    def test_issue_26(self):
        path = testdata.create_modules({
            "foo_test": [],
            "foo_test.bar": [],
            "foo_test.bar.che_test": [
                "from unittest import TestCase",
                "",
                "class Issue26TestCase(TestCase):",
                "   def test_boo(self):",
                "       pass",
            ]
        })

        pf = PathFinder(
            basedir=path,
            module_name="che",
            prefix="foo/bar",
            filepath="",
        )
        self.assertEqual(1, len(list(pf.paths())))

        pf = PathFinder(
            basedir=path,
            module_name="foo",
            prefix="",
            filepath="",
        )
        self.assertEqual(2, len(list(pf.paths())))

        pf = PathFinder(
            basedir=path,
            method_name="boo",
            class_name="Issue26",
            module_name="bar",
            prefix="foo_test",
            filepath="",
        )
        ti = PathGuesser("foo_test.bar.Issue26.boo", path)
        self.assertEqual("test_boo", list(pf.method_names())[0][1])

        pf = PathFinder(
            basedir=path,
            module_name="bar",
            prefix="foo",
            filepath="",
        )
        self.assertEqual(1, len(list(pf.paths())))

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

    def test_module_path(self):
        m = TestModule(
            "class ModulePathCase(TestCase):",
            "   def test_one(self): pass",
        )
        pf = m.pathfinder

        m2 = TestModule(
            "class ModulePath2Case(TestCase):",
            "   def test_two(self): pass",
        )
        r = pf.module_path(m2.path)
        self.assertEqual(m2.module, r)

        r = pf.module_path(m.path)
        self.assertEqual(m.module, r)

    def test_testnames(self):
        m = TestModule(
            [
                "class TestbarTest(TestCase):",
                "    def test_foo(self):",
                "        pass",
            ],
            name="testbar_test"
        )

        r = m.client.run("testbar.Testbar.foo")
        self.assertTrue("Ran 1 test" in r)

        r = m.client.run("testbar.TestbarTest.foo")
        self.assertTrue("Ran 1 test" in r)

        r = m.client.run("testbar_test.TestbarTest.foo")
        self.assertTrue("Ran 1 test" in r)

        r = m.client.run("testbar_test.Testbar.foo")
        self.assertTrue("Ran 1 test" in r)


class PathGuesserTest(TestCase):
    def test_filename(self):
        ti = PathGuesser("foo/bar/che.py", '/tmp')
        self.assertEqual(1, len(list(ti.possible)))
        p = list(ti.possible)[0]
        self.assertEqual("/tmp/foo/bar/che.py", list(p.paths())[0])

        ti = PathGuesser("/foo/bar/che.py", '/tmp')
        self.assertEqual(1, len(list(ti.possible)))
        p = list(ti.possible)[0]
        self.assertEqual("/foo/bar/che.py", list(p.paths())[0])

        ti = PathGuesser("/foo/bar.py:Che.baz", "/tmp")
        p = list(ti.possible)[0]
        self.assertEqual("Che", p.class_name)
        self.assertEqual("baz", p.method_name)
        self.assertEqual("/foo/bar.py", p.filepath)

        ti = PathGuesser("/foo/bar.py:baz", "/tmp")
        p = list(ti.possible)[0]
        with self.assertRaises(AttributeError):
            p.class_name
        self.assertEqual("baz", p.method_name)
        self.assertEqual("/foo/bar.py", p.filepath)

    def test_set_possible(self):
        tests = (
            ('foo.bar', [
                {'module_name': 'bar', 'prefix': 'foo'},
                {'method_name': 'bar', 'module_name': 'foo', 'prefix': ''}
            ]),
            ('foo.Bar', [
                {'module_name': 'foo', 'class_name': 'Bar', 'prefix': ''}
            ]),
            (
                'foo.Bar.baz',
                [
                    {
                        'module_name': 'foo',
                        'class_name': 'Bar',
                        'prefix': '',
                        'method_name': 'baz'
                    }
                ]
            ),
            (
                'prefix.foo.Bar.baz',
                [
                    {
                        'module_name': 'foo',
                        'class_name': 'Bar',
                        'prefix': 'prefix',
                        'method_name': 'baz'
                    }
                ]
            ),
            (
                'pre.fix.foo.Bar.baz',
                [
                    {
                        'module_name': 'foo',
                        'class_name': 'Bar',
                        'prefix': 'pre/fix',
                        'method_name': 'baz'
                    }
                ]
            ),
            (
                'Call.controller',
                [
                    {
                        'class_name': 'Call',
                        'method_name': 'controller',
                        'prefix': '',
                        'module_name': ''
                    }
                ]
            ),
            (
                'Call',
                [
                    {'class_name': 'Call', 'prefix': '', 'module_name': ''}
                ]
            ),
            ('Boom.fooBar', [
                {
                    'class_name': 'Boom',
                    'prefix': '',
                    'module_name': '',
                    'method_name': 'fooBar'
                }
            ]),
            (
                'get_SQL',
                [
                    {'module_name': 'get_SQL', 'prefix': ''},
                    {'method_name': 'get_SQL', 'module_name': '', 'prefix': ''}
                ]
            ),
            (
                'prefix1.prefix2.modname:ClassName.method_name',
                [
                    {
                        'class_name': 'ClassName',
                        'prefix': 'prefix1.prefix2',
                        'module_name': 'modname',
                        'method_name': 'method_name'
                    }
                ]
            ),
            (
                'modname:ClassName',
                [
                    {
                        'class_name': 'ClassName',
                        'module_name': 'modname',
                        'method_name': None,
                    }
                ]
            ),
            (
                'modname:method_name',
                [
                    {
                        'class_name': None,
                        'module_name': 'modname',
                        'method_name': 'method_name'
                    }
                ]
            ),
        )

        basedir = testdata.create_dir()

        for test_in, test_out in tests:
            ti = PathGuesser(test_in, basedir)
            for i, to in enumerate(test_out):
                for k, v in to.items():
                    r = getattr(ti.possible[i], k, None)
                    self.assertEqual(v, r, test_in)

    def test_no_name(self):
        ti = PathGuesser('', testdata.create_dir())
        self.assertEqual(1, len(ti.possible))


class RerunFileTest(TestCase):
    def test_rerun(self):
        m = TestModule(
            "class RerunTestCase(TestCase):",
            "    def test_success(self):",
            "        pass",
            "",
            "    def test_error(self):",
            "        raise ValueError()",
            "",
            "    def test_failure(self):",
            "        self.assertTrue(False)",
            "",
        )
        s = m.client

        r = s.run("--verbose", code=1)

        rf = RerunFile()
        for line in rf:
            self.assertTrue(line)
            self.assertTrue(line in rf)

        r = s.run("--rerun", code=1)
        self.assertTrue("Ran 2 tests" in r)
        for line in rf:
            self.assertTrue(line)
            self.assertTrue(line in rf)

