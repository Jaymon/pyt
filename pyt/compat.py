# -*- coding: utf-8 -*-

import sys

# shamelessly ripped from https://github.com/kennethreitz/requests/blob/master/requests/compat.py
# Syntax sugar.
_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)

if is_py2:
    from StringIO import StringIO

    basestring = basestring
    range = xrange # range is now always an iterator

    # http://stackoverflow.com/questions/14503751
    # ripped from six https://bitbucket.org/gutworth/six
    exec("""def reraise(tp, value, tb=None):
        try:
            raise tp, value, tb
        finally:
            tb = None
    """)


elif is_py3:
    from io import StringIO

    basestring = (str, bytes)

    # ripped from six https://bitbucket.org/gutworth/six
    def reraise(tp, value, tb=None):
        try:
            if value is None:
                value = tp()
            if value.__traceback__ is not tb:
                raise value.with_traceback(tb)
            raise value
        finally:
            value = None
            tb = None


    # this code was for trying to fix this issue:
    # https://github.com/Jaymon/pyt/issues/24
    # maybe use imp.load_module for py2 version:
    # https://docs.python.org/3/library/imp.html#imp.load_module
#     import importlib.util
#     import hashlib
# 
#     def import_path(path):
#         # https://docs.python.org/3/library/importlib.html#importing-a-source-file-directly
#         module_name = hashlib.md5(str(path).encode("utf-8")).hexdigest()
#         spec = importlib.util.spec_from_file_location(module_name, path)
#         module = importlib.util.module_from_spec(spec)
#         spec.loader.exec_module(module)
#         return module
