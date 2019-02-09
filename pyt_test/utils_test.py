# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import


from pyt.utils import classpath, testpath
from . import TestCase


class UtilsTest(TestCase):
    def test_classpath(self):
        s = "pyt_test.utils_test.UtilsTest"
        r = classpath(self)
        self.assertEqual(s, r)

        r = classpath(UtilsTest)
        self.assertEqual(s, r)

    def test_testpath(self):
        self.skipTest("")
        tc = TestCase("test_foo")
        r = testpath(tc)

