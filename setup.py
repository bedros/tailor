#!/usr/bin/env python

from distutils.core import setup

setup(name='tailor',
    version='devel-2005-02-10',
    author='Lele Gaifax',
    author_email='lele@nautilus.homeip.net',
    packages=['vcpx'],
    scripts=['tailor.py'],
    description='a tool to migrate changesets between CVS, Subversion, and darcs repositories.',
    long_description="""\
This script makes it easier to keep the upstream changes merged in
a branch of a product, storing needed information such as the upstream
URI and revision in special properties on the branched directory.
""",
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Operating System :: Unix',
        'Topic :: Software Development :: Version Control',
        # Don't know license
        # Don't know the stability. Took a guess
        ]
    )
