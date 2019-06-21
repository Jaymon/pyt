# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
from unittest import TestCase # to allow from pyt import TestCase
from unittest import ( # so pyt can be a one-stop shop for skipping
    SkipTest,
    skip,
    skipIf,
    skipIf as skip_if,
    skipUnless,
    skipUnless as skip_unless
)
import os
import logging
import sys


from .tester import main # so you can do pyt.main like unittest.main


__version__ = '1.0.5'


def get_counts():
    """return test counts that are set via pyt environment variables when pyt 
    runs the test

    :returns: dict, 3 keys (classes, tests, modules) and how many tests of each
        were found by pyt
    """
    counts = {}
    ks = [
        ('PYT_TEST_CLASS_COUNT', "classes"),
        ('PYT_TEST_COUNT', "tests"),
        ('PYT_TEST_MODULE_COUNT', "modules"),
    ]

    for ek, cn in ks:
        counts[cn] = int(os.environ.get(ek, 0))

    return counts


def is_single_class():
    """Returns True if only a single class is being run or some tests within a single class"""
    ret = False
    counts = get_counts()
    if counts["classes"] < 1 and counts["modules"] < 1:
        ret = counts["tests"] > 0
    else:
        ret = counts["classes"] <= 1 and counts["modules"] <= 1
    return ret


def skip_multi_class(msg=""):
    """will raise msg if multiple classes are being ran"""
    if not is_single_class():
        raise SkipTest(msg)


def is_single_module():
    """Returns True if only a module is being run"""
    ret = False
    counts = get_counts()
    if counts["modules"] == 1:
        ret = True

    elif counts["modules"] < 1:
        ret = is_single_class()

    return ret


def skip_multi_module(msg=""):
    """Will raise msg if multiple modules are being ran"""
    if not is_single_module():
        raise SkipTest(msg)


def is_single_test():
    """Returns True if only a single function is being run"""
    counts = get_counts()
    return counts["tests"] == 1


def skip_multi_test(msg=""):
    """Skip this test if there are multiple tests that are being run"""
    counts = get_counts()
    if not is_single_test():
        raise SkipTest(msg)

