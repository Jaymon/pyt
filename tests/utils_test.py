# -*- coding: utf-8 -*-

from pyt.utils import classpath, testpath
from . import TestCase


class UtilsTest(TestCase):
    def test_classpath(self):
        s = "tests.utils_test.UtilsTest"
        r = classpath(self)
        self.assertEqual(s, r)

        r = classpath(UtilsTest)
        self.assertEqual(s, r)

