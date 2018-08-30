#!/usr/bin/env python
from setuptools import setup, find_packages
import re
import os
import sys
from codecs import open


_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)


def read(path):
    if os.path.isfile(path):
        with open(path, encoding='utf-8') as f:
            return f.read()
    return ""


name = 'pyt'
vpath = os.path.join(name, "__init__.py")
version = re.search("^__version__\s*=\s*[\'\"]([^\'\"]+)", read(vpath), flags=re.I | re.M).group(1)
long_description = read('README.rst')

kwargs = dict(
    name=name,
    version=version,
    description='easily run python unit tests',
    long_description=long_description,
    author='Jay Marcyes',
    author_email='jay@marcyes.com',
    url='http://github.com/Jaymon/{}'.format(name),
    packages=[name],
    license="MIT",
    classifiers=[ # https://pypi.python.org/pypi?:action=list_classifiers
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Software Development :: Testing',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
    ],
    #test_suite = "test_pout",
)

if is_py2:
    kwargs['entry_points'] = {
        'console_scripts': [
            '{} = {}.__main__:console'.format(name, name),
            '{}2 = {}.__main__:console'.format(name, name)
        ]
    }

else:
    kwargs['entry_points'] = {
        'console_scripts': [
            '{} = {}.__main__:console'.format(name, name),
            '{}3 = {}.__main__:console'.format(name, name)
        ]
    }

setup(**kwargs)

