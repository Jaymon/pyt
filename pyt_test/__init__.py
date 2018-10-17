# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import os
import sys

import testdata
from testdata.client import ModuleCommand
from testdata import TestCase

# remove any global pyt
# NOTE -- when I actually got rid of the modules (just the .pop() without the
# reassignment to bak.) it caused all kinds of strange and subtle issues, but
# only when I was running the tests with a global pyt
for k in list(sys.modules.keys()):
    if k.startswith("pyt.") or k == "pyt":
        sys.modules["bak.{}".format(k)] = sys.modules.pop(k)

from pyt import tester
from pyt.compat import *
from pyt.path import PathFinder, PathGuesser
from pyt.tester import TestLoader, main
from pyt.environ import TestEnviron


#echo.DEBUG = True
#testdata.basic_logging()
environ = tester.TestEnviron.get_instance()
environ.debug = True


class Client(ModuleCommand):
    name = "pyt"
#     @property
#     def environ(self):
#         environ = super(Client, self).environ
#         if os.getcwd() not in environ["PYTHONPATH"]:
#             environ["PYTHONPATH"] = os.getcwd() + os.pathsep + environ["PYTHONPATH"]
#         return environ

#     def __init__(self, cwd):
#         super(Client, self).__init__("pyt", cwd=cwd)

#     def create_cmd(self, arg_str):
#         prefix_arg_str = '--basedir="{}"'.format(self.cwd)
#         if arg_str:
#             arg_str = prefix_arg_str + " " + arg_str
#         else:
#             arg_str = prefix_arg_str
#         return super(Client, self).create_cmd(arg_str)


class TestModule(object):
    @property
    def basedir(self):
        return self.cwd

    @property
    def client(self):
        return Client(cwd=self.cwd)

#     @property
#     def test(self):
#         t = Test()
#         t.module_name = self.name
#         return t

    @property
    def tl(self):
        tl = TestLoader(self.cwd, TestEnviron())
        return tl
    loader = tl

    @property
    def tci(self):
        """return a PathFinder instance for this module"""
        tc = PathFinder(
            self.cwd,
            module_name=self.module_name, 
            prefix=self.prefix
        )
        return tc
    pathfinder = tci

    def __init__(self, *body, **kwargs):
        if "cwd" in kwargs:
            self.cwd = kwargs["cwd"]
        else:
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

        if len(body) == 1: body = body[0]
        self.body = body
        if isinstance(self.body, dict):
            for k in self.body:
                self.body[k] = self._prepare_body(self.body[k])
            self.path = testdata.create_modules(
                self.body,
                self.cwd,
                prefix=self.name,
            )

        else:
            self.path = testdata.create_module(
                self.name,
                self._prepare_body(self.body),
                self.cwd
            )

    def _prepare_body(self, body):
        import_str = "from unittest import TestCase"
        if isinstance(body, basestring):
            body = list(body.splitlines(False))
        else:
            body = list(body)

        if import_str not in body:
            if "__future__" in body[0]:
                body.insert(1, import_str)
            else:
                body.insert(0, import_str)

        return body

    def run(self, name="", **kwargs):
        if not name:
            name = self.name
        r = main(
            self.name,
            self.cwd,
            **kwargs
        )
        return r


