# -*- coding: utf-8 -*-
import os
import sys
import logging
from collections import Counter


from .compat import *


class TestEnviron(object):
    """This is the Test environment, it manages what the actual test environment
    will look like in certain respects and works as a bridge between the passed
    in cli arguments and settings on the TestCases
    """
    def __init__(self, **kwargs):
        self.counter = Counter()

    def update_env_for_test(self, test_count):
        # not sure how much I love messing with the environment right here, but
        # this does propagate down to the test cases
        self.test_count = test_count
        os.environ['PYT_TEST_COUNT'] = str(test_count)
        os.environ['PYT_TEST_METHOD_COUNT'] = str(self.counter["methods"])
        os.environ['PYT_TEST_CLASS_COUNT'] = str(self.counter["classes"])
        os.environ['PYT_TEST_MODULE_COUNT'] = str(self.counter["modules"])

    def get_prefixes(self, environ_key="PYT_PREFIX"):
        """Return all the environment prefixes as a list

        https://github.com/Jaymon/pyt/issues/44

        :param environ_key: str, should probably not be touched
        :returns: list[str], the prefixes
        """
        ret = []
        for prefixes in self.nkeys(environ_key):
            ret.extend(prefixes.split(os.pathsep))

        return ret

    def nkeys(self, key):
        """This returns the actual environment variable names from * -> *_N

        Ripped/modified from datatypes.environ.Environ (I combined both .nkeys
        and nkey) on 2-20-2024

        :param key: str, the name of the environment variables
        :returns: generator[str], the found environment names
        """
        if key in os.environ:
            yield key

        # now try importing _1 -> _N prefixes
        n = 0
        while True:
            found = False
            for fmt in ["{key}_{n}", "{key}{n}"]:
                nkey = fmt.format(key=key, n=n)
                if nkey in os.environ:
                    found = True
                    yield nkey
                    break

            if not found:
                if n:
                    break

                else:
                    # 0 is a special case, so if it fails we keep going
                    found = True

            n += 1

