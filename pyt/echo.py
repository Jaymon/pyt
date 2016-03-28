# -*- coding: utf-8 -*-
import sys
import os

DEBUG = False

stderr = sys.stderr
#stdout = sys.stdout

stddbg = stderr


def configure(environ):
    global DEBUG
    global stddbg
    if environ.debug:
        DEBUG = True
        stddbg = environ.stderr_stream


def _build_str(format_str, *args, **kwargs):
    s = format_str
    if isinstance(format_str, basestring):
        if args or kwargs:
            s = s.format(*args, **kwargs)

    else:
        s = str(format_str)

    return s


def _write_str(s, stream):
    stream.write(str(s)) 
    stream.write(os.linesep)
    stream.flush()


def out(format_str, *args, **kwargs):
    global stderr
    _write_str(_build_str(format_str, *args, **kwargs), stderr)


def debug(format_str, *args, **kwargs):
    global DEBUG
    global stddbg
    if DEBUG:
        _write_str(_build_str(format_str, *args, **kwargs), stddbg)

