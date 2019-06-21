# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
from unittest.util import strclass
from unittest import TestCase
import itertools
import logging
import inspect
from collections import namedtuple


def testpath(test, method_name=""):
    """Returns the full classpath (eg prefix.module.Class.method) for a passed in
    test

    :param test: TestCase, the test case instance
    :returns: string, the full testpath
    """
    if not method_name:
        try:
            method_name = test._testMethodName
        except AttributeError:
            pass

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


def modname():
    """Returns the main module name (so this should return "pyt")"""
    name = __name__.split(".")[0]
    return name


def loghandler_members():
    """iterate through the attributes of every logger's handler

    this is used to switch out stderr and stdout in tests when buffer is True

    :returns: generator of tuples, each tuple has (name, handler, member_name, member_val)
    """
    Members = namedtuple("Members", ["name", "handler", "member_name", "member"])
    log_manager = logging.Logger.manager
    loggers = []
    ignore = set([modname()])
    if log_manager.root:
        loggers = list(log_manager.loggerDict.items())
        loggers.append(("root", log_manager.root))

    for logger_name, logger in loggers:
        if logger_name in ignore: continue

        for handler in getattr(logger, "handlers", []):
            members = inspect.getmembers(handler)
            for member_name, member in members:
                yield Members(logger_name, handler, member_name, member)


