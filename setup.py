#!/usr/bin/env python
from setuptools import setup, find_packages
import re
import os


name = 'pyt'
with open(os.path.join(name, "__init__.py")) as f:
    version = re.search("^__version__\s*=\s*[\'\"]([^\'\"]+)", f.read(), flags=re.I | re.M).group(1)

setup(
    name=name,
    version=version,
    description='easily run python unit tests',
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
        'Programming Language :: Python :: 3.5',
    ],
    #test_suite = "test_pout",
    entry_points = {
        'console_scripts': ['{} = {}.__main__:console'.format(name, name)]
    },
)
