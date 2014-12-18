# Release procedure:
#  - fill the changelog
#  - run unit tests on Linux: run "tox"
#  - run unit tests on Windows, run::
#
#       \Python27\python.exe runtests.py -r
#
#  - update the version in setup.py to X.Y
#  - set release date in README
#  - check that "python setup.py sdist" contains all files tracked by
#    the SCM (Mercurial): update MANIFEST.in if needed
#  - hg ci
#  - hg tag X.Y
#  - hg push
#  - python setup.py sdist bdist_wheel register upload
#  - increment version in setup.py
#  - hg ci && hg push

import sys
try:
    from setuptools import setup
    SETUPTOOLS = True
except ImportError:
    SETUPTOOLS = False
    # Use distutils.core as a fallback.
    # We won't be able to build the Wheel file on Windows.
    from distutils.core import setup

requirements = ['gevent']
if sys.version_info >= (3, 4):
    # Python 3.4 and newer: asyncio is now part of the stdlib
    pass
elif (3, 3) <= sys.version_info < (3, 4):
    # Python 3.3: use Tulip
    requirements.append('asyncio>=0.4.1')
else:
    # Python 2.6-3.2: use Trollius
    requirements.append('trollius>=0.3')

with open("README") as fp:
    long_description = fp.read()

install_options = {
    "name": "aiogevent",
    "version": "0.3",
    "license": "Apache License 2.0",
    "author": 'Victor Stinner',
    "author_email": 'victor.stinner@gmail.com',

    "description": "asyncio API (PEP 3156) implemented on top of gevent",
    "long_description": long_description,
    "url": "https://pypi.python.org/pypi/aiogevent",

    "classifiers": [
        "Programming Language :: Python",
        #"Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
    ],

    "py_modules": ["aiogevent"],
    #"test_suite": "runtests.runtests",
}
if SETUPTOOLS:
    install_options['install_requires'] = requirements

setup(**install_options)
