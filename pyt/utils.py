# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
from unittest.util import strclass
import itertools


def testpath(test, method_name=""):
    """Returns the full classpath (eg prefix.module.Class.method) for a passed in
    test

    :param test: TestCase, the test case instance
    :returns: string, the full testpath
    """
    if not method_name:
        method_name = test._testMethodName

    return "{}.{}".format(classpath(test), method_name)


def classpath(v):
    """given a class/instance return the full class path (eg, prefix.module.Classname)

    :param v: class or instance
    :returns: string, the full classpath of v
    """
    if isinstance(v, type):
        ret = strclass(v)
    else:
        ret = strclass(v.__class__)
    return ret


def chain(*sequences):
    """wrapper around itertools.chain

    :param *sequences: one or more sequences (eg, list, tuple, iterator) that you
        want to iterate through one right after another, if you pass in one sequence
        it will be assumed to be a list of sequences
    :returns: iterator, a generator that will work through each passed sequence
    """
    if len(sequences) == 1:
        sequences = sequences[0]
    return itertools.chain(*sequences)

