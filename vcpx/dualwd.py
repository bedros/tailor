#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Dual working directory
# :Creato:   dom 20 giu 2004 11:02:01 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
The easiest way to propagate changes from one VC control system to one
of an another kind is having a single directory containing a live
working copy shared between the two VC systems.

This module implements `DualWorkingDir`, which instances have a
`source` and `target` properties offering the right capabilities to do
the job.
"""

__docformat__ = 'reStructuredText'

from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir
from svn import SvnWorkingDir
from cvs import CvsWorkingDir
from darcs import DarcsWorkingDir

class DualWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    """
    Dual working directory, one that is under two different VC systems at
    the same time.

    This class reimplements the two interfaces, dispatching the right method
    to the right instance.
    """

    def __init__(self, source_kind, target_kind):
        globs = globals()
        
        self.source = globs[source_kind.capitalize() + 'WorkingDir']()
        self.target = globs[target_kind.capitalize() + 'WorkingDir']()

    ## UpdatableSourceWorkingDir
        
    def applyUpstreamChangesets(self, root, replay=None):
        return self.source.applyUpstreamChangesets(root,
                                                   self.target.replayChangeset)
        
    def checkoutUpstreamRevision(self, root, repository, revision):
        return self.source.checkoutUpstreamRevision(root, repository, revision)

    ## SyncronizableTargetWorkingDir
    
    def initializeNewWorkingDir(self, root, repository, revision):
        self.target.initializeNewWorkingDir(root, repository, revision)

    ## Facilities
        
    def bootstrap(self, root, repository, revision):
        """
        Bootstrap a new tailorized module.

        Extract a copy of the `repository` at given `revision` in the `root`
        directory and initialize a target repository with its content.
        """
        
        actual = self.checkoutUpstreamRevision(root, repository, revision)
        self.initializeNewWorkingDir(root, repository, actual)

if __name__ == '__main__':
##     dwd = DualWorkingDir('svn', 'darcs')
##     dwd.bootstrap('/tmp/prove/provapyde',
##                   'svn+ssh://caia/ND/svn/tests/provapyde',
##                   '1')
##     dwd.applyUpstreamChangesets('/tmp/prove/provapyde')

##     dwd = DualWorkingDir('cvs', 'darcs')
##     dwd.bootstrap('/tmp/prove/PyApache', '/usr/local/CVSROOT/', 'HEAD')
##     dwd.applyUpstreamChangesets('/tmp/prove/PyApache')
    
    dwd = DualWorkingDir('cvs', 'svn')
    dwd.bootstrap('/tmp/prove/reportman', ':pserver:anonymous@cvs.sourceforge.net:/cvsroot/reportman', 'HEAD')
    dwd.applyUpstreamChangesets('/tmp/prove/reportman')

##     dwd = DualWorkingDir('svn', 'darcs')
##     dwd.bootstrap('/tmp/prove/CMFPlone',
##                   'http://svn.plone.org/plone/CMFPlone/branches/Plone-2_0-branch',
##                   '4818')
##     dwd.applyUpstreamChangesets('/tmp/prove/CMFPlone')
    
