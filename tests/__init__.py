# -*- coding: utf-8 -*-
import os
import sys
import logging

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
for n, l in list(logging.Logger.manager.loggerDict.items()):
    if n.startswith("pyt.") or n == "pyt":
        new_n = "bak.{}".format(n)
        l.name = new_n
        logging.Logger.manager.loggerDict.pop(n)
        logging.Logger.manager.loggerDict[new_n] = l


from pyt.compat import *
from pyt.path import PathFinder, PathGuesser
from pyt.tester import TestLoader, main, TestProgram
from pyt.environ import TestEnviron


testdata.basic_logging(
#     format="|".join([
#         '[%(levelname).1s',
#         '%(asctime)s',
#         '%(process)d.%(thread)d',
#         '%(name)s', # logger name
#         '%(pathname)s:%(lineno)s] %(message)s',
#     ]),
)


class TestModule(object):
    @property
    def basedir(self):
        return self.cwd

    @property
    def client(self):
        return ModuleCommand("pyt", cwd=self.cwd)

    @property
    def loader(self):
        tl = TestLoader()
        tl._top_level_dir = self.cwd
        tl.program = testdata.mock(environ=TestEnviron())
        return tl
    tl = loader

    @property
    def pathfinder(self):
        """return a PathFinder instance for this module"""
        tc = PathFinder(
            self.cwd,
            module_name=self.module_name, 
            prefix=self.prefix
        )
        return tc
    tci = pathfinder
    finder = pathfinder

    def __init__(self, *body, **kwargs):
        if "cwd" in kwargs:
            self.cwd = kwargs["cwd"]

        else:
            self.cwd = testdata.create_dir()

        name = kwargs.get('name', None)
        if name is not None:
            self.name = name

        else:
            self.name = "prefix{}.pmod{}_test".format(
                testdata.get_ascii(5).lower(),
                testdata.get_ascii(5).lower()
            )

        self.module_name = ""
        self.prefix = ""
        self.name_prefix = ""
        if self.name:
            bits = self.name.rsplit('.', 1)
            self.module_name = bits[1] if len(bits) == 2 else bits[0]
            self.prefix = bits[0] if len(bits) == 2 else ''
            self.name_prefix = bits[1][:4] if len(bits) == 2 else bits[0][:4]

        if len(body) == 1:
            body = body[0]

        self.body = body

        if isinstance(self.body, dict):
            for k in self.body:
                self.body[k] = self._prepare_body(self.body[k])

            self.modules = testdata.create_modules(
                self.body,
                modpath=self.name,
                tmpdir=self.cwd,
            )
            self.path = self.modules.path

        else:
            if kwargs.get("package", False):
                self.module = testdata.create_package(
                    self._prepare_body(self.body),
                    modpath=self.name,
                    tmpdir=self.cwd
                )

            else:
                self.module = testdata.create_module(
                    self._prepare_body(self.body),
                    modpath=self.name,
                    tmpdir=self.cwd
                )

            self.path = self.module.path

    def _prepare_body(self, body):
        if isinstance(body, basestring):
            body = list(body.splitlines(False))

        else:
            body = list(body)

        ret = [
            "# -*- coding: utf-8 -*-",
            "from unittest import TestCase",
            "import pyt",
        ]
        ret.extend(body)
        ret.append("")
        return ret

    def run(self, name="", **kwargs):
        if not name:
            name = self.name

        loader = self.loader # we pass in the loader so cwd will be set
        r = TestProgram(
            module=None,
            argv=[self.__class__.__name__, name],
            testLoader=loader,
            exit=False,
            **kwargs
        )
        return r


