# -*- coding: utf-8 -*-
from __future__ import unicode_literals, division, print_function, absolute_import
import sys
import logging
from collections import Counter


from .compat import *


logging.basicConfig(format="%(message)s", level=logging.WARNING, stream=sys.stderr)


class TestEnviron(object):
    """This is the Test environment, it manages what the actual test environment
    will look like in certain respects and works as a bridge between the passed in
    cli arguments and settings on the TestCases
    """
    stdout_stream = sys.stdout
    stderr_stream = sys.stderr

    stdout_buffer = StringIO()
    stderr_buffer = StringIO()

    _instance = None
    """singleton"""

    @property
    def debug(self):
        return self._debug

    @debug.setter
    def debug(self, v):
        logger_name = __name__.split(".")[0]
        logger = logging.getLogger(logger_name)
        if v:
            logger.setLevel(logging.DEBUG)
            # stddbg = environ.stderr_stream
        else:
            logger.setLevel(logging.WARNING)
        self._debug = v

    @property
    def buffer(self):
        return self._buffer

    @buffer.setter
    def buffer(self, v):
        if v:
            sys.stdout = self.stdout_buffer
            sys.stderr = self.stderr_buffer

        else:
            if sys.stdout is not self.stdout_stream:
                sys.stdout = self.stdout_stream

            if sys.stderr is not self.stderr_stream:
                sys.stderr = self.stderr_stream
        self._buffer = v

    def __init__(self, **kwargs):
        self.buffer = kwargs.pop("buffer", False)
        self.debug = kwargs.pop("debug", False)
        self.warnings = kwargs.pop("warnings", False)
        self.counter = Counter()

    @classmethod
    def get_instance(cls, **kwargs):
        if kwargs or not cls._instance:
            cls._instance = cls(**kwargs)
        return cls._instance

    def unbuffer(self):
        self.buffer = False

    def update_env_for_test(self, test_count):
        # not sure how much I love messing with the environment right here, but this
        # does propagate down to the test cases
        os.environ['PYT_TEST_COUNT'] = str(test_count)
        os.environ['PYT_TEST_METHOD_COUNT'] = str(self.counter["methods"])
        os.environ['PYT_TEST_CLASS_COUNT'] = str(self.counter["classes"])
        os.environ['PYT_TEST_MODULE_COUNT'] = str(self.counter["modules"])


