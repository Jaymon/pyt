import unittest
import os

import pyt

class PytTest(unittest.TestCase):
    def test_find_test_info(self):
        tests = (
            ('foo.bar', [{'module': 'bar', 'prefix': 'foo'}, {'method': 'bar', 'module': 'foo', 'prefix': ''}]),
            ('foo.Bar', [{'module': 'foo', 'class': 'Bar', 'prefix': ''}]),
            ('foo.Bar.baz', [{'module': 'foo', 'class': 'Bar', 'prefix': '', 'method': 'baz'}]),
            ('prefix.foo.Bar.baz', [{'module': 'foo', 'class': 'Bar', 'prefix': 'prefix', 'method': 'baz'}]),
            ('pre.fix.foo.Bar.baz', [{'module': 'foo', 'class': 'Bar', 'prefix': 'pre/fix', 'method': 'baz'}]),
        )

        for test_in, test_out in tests:
            ret = pyt.find_test_info(test_in)
            self.assertEqual(ret, test_out)

    def test_find_test_module(self):
        self.assertEqual(0, 1)
        pass
        #pyt.find_test_module({}, os.curdir)


