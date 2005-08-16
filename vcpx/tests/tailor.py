# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Operational tests
# :Creato:   lun 08 ago 2005 22:17:10 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
[DEFAULT]
dont-refill-changelogs = True
target-module = None
source-repository = ~/WiP/cvsync
encoding = None
target-repository = None
use-svn-propset = False
source-module = None
update = True
subdir = .
debug = True
remove-first-log-line = False
patch-name-format = None
verbose = True
state-file = tailor.state
start-revision = Almost arbitrarily tagging this as version 0.8

[darcs2bzr]
target = bzr:tailor
root-directory = /tmp/tailor-tests/darcs2bzr
source = darcs:tailor

[darcs2cdv]
target = cdv:tailor
root-directory = /tmp/tailor-tests/darcs2cdv
source = darcs:tailor

[darcs2hg]
target = hg:tailor
root-directory = /tmp/tailor-tests/darcs2hg
source = darcs:tailor

[darcs2svn]
target = svn:tailor
root-directory = /tmp/tailor-tests/darcs2svn
source = darcs:tailor
start-revision = INITIAL

[svn2darcs]
target = darcs:svntailor
root-directory = /tmp/tailor-tests/svn2darcs
source = svn:tailor
start-revision = 1

[darcs:tailor]
repository = ~/WiP/cvsync

[bzr:tailor]
bzr-command = /opt/src/bzr.dev/bzr

[cdv:tailor]

[hg:tailor]

[svn:tailor]
repository = file:///tmp/tailor-tests/svnrepo
module = tailor
"""

from unittest import TestCase, TestSuite
from cStringIO import StringIO
from vcpx.config import Config
from vcpx.tailor import Tailorizer

class TailorTest(TestCase):

    def setUp(self):
        from os import mkdir
        from os.path import exists
        from atexit import register
        from shutil import rmtree

        self.config = Config(StringIO(__doc__), {})
        if not exists('/tmp/tailor-tests'):
            mkdir('/tmp/tailor-tests')
            register(rmtree, '/tmp/tailor-tests')

    def testDarcsToBazaarngBootstrap(self):
        "Test darcs to BazaarNG bootstrap"

        project = self.config['darcs2bzr']
        tailorizer = Tailorizer(project)
        tailorizer()

    def testDarcsToBazaarngUpdate(self):
        "Test darcs to BazaarNG update"

        project = self.config['darcs2bzr']
        tailorizer = Tailorizer(project)
        tailorizer()

    def testDarcsToMercurialBootstrap(self):
        "Test darcs to mercurial bootstrap"

        project = self.config['darcs2hg']
        tailorizer = Tailorizer(project)
        tailorizer()

    def testDarcsToMercurialUpdate(self):
        "Test darcs to mercurial update"

        project = self.config['darcs2hg']
        tailorizer = Tailorizer(project)
        tailorizer()

    def testDarcsToCodevilleBootstrap(self):
        "Test darcs to codeville bootstrap"

        project = self.config['darcs2cdv']
        tailorizer = Tailorizer(project)
        tailorizer()

    def testDarcsToCodevilleUpdate(self):
        "Test darcs to codeville update"

        project = self.config['darcs2cdv']
        tailorizer = Tailorizer(project)
        tailorizer()

    def testDarcsToSubversionBootstrap(self):
        "Test darcs to subversion bootstrap"

        project = self.config['darcs2svn']
        tailorizer = Tailorizer(project)
        tailorizer()

    def testDarcsToSubversionUpdate(self):
        "Test darcs to subversion update"

        project = self.config['darcs2svn']
        tailorizer = Tailorizer(project)
        tailorizer()

    ## The other way

    def testSubversionToDarcsBootstrap(self):
        "Test reversed darcs to subversion bootstrap"

        project = self.config['svn2darcs']
        tailorizer = Tailorizer(project)
        tailorizer()

    def testSubversionToDarcsUpdate(self):
        "Test reversed darcs to subversion update"

        project = self.config['svn2darcs']
        tailorizer = Tailorizer(project)
        tailorizer()
