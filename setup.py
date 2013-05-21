#!/usr/bin/env python
# I shamefully ripped most of this off from fbconsole
# http://docs.python.org/distutils/setupscript.html
# http://docs.python.org/2/distutils/examples.html

import sys
from setuptools import setup

version = '0.3.1'

setup(
    name='pyt',
    version=version,
    description='easily run python unit tests',
    author='Jay Marcyes',
    author_email='jay@marcyes.com',
    url='http://github.com/Jaymon/pyt',
    py_modules=['pyt'],
    license="MIT",
    classifiers=[
        'Development Status :: {}'.format(version),
        'Environment :: Console',
        'Intended Audience :: Developers',
        'License :: MIT',
        'Operating System :: OS Independent',
        'Topic :: Utilities',
    ],
    #test_suite = "test_pout",
    entry_points = {
        'console_scripts': ['pyt = pyt:console']
    }
)
