# -*- coding: utf-8 -*-
import sys
import os

DEBUG = False

def out(format_str, *args, **kwargs):
    if isinstance(format_str, basestring):
        sys.stderr.write(format_str.format(*args, **kwargs)) 
        sys.stderr.write(os.linesep)
        sys.stderr.flush()

    else:
        sys.stderr.write(str(format_str)) 
        sys.stderr.write(os.linesep)
        sys.stderr.flush()


def debug(*args, **kwargs):
    global DEBUG
    if DEBUG:
        out(*args, **kwargs)
