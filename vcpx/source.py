#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Updatable VC working directory
# :Creato:   mer 09 giu 2004 13:55:35 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
#

"""
Updatable sources are the simplest abstract wrappers around a working
directory under some kind of version control system.
"""

__docformat__ = 'reStructuredText'

CONFLICTS_PROMPT = """
The changeset

%s
caused conflicts on the following files:

 * %s

Either abort the session with Ctrl-C, or manually correct the situation
with a Ctrl-Z and a few "svn resolved". What would you like to do?
"""

class UpdatableSourceWorkingDir(object):
    """
    This is an abstract working dir able to follow an upstream
    source of `changesets`.

    It has two main functionalities:

    applyUpstreamChangesets
        to query the upstream server about new changesets and
        apply them to the working directory

    checkoutUpstreamRevision
        to extract a new copy of the sources, actually initializing
        the mechanism.
      
    Subclasses MUST override at least the _underscoredMethods.
    """

    def applyUpstreamChangesets(self, root, sincerev, replay=None):
        """
        Apply the collected upstream changes.

        Loop over the collected changesets, doing whatever is needed
        to apply each one to the working dir and if the changes do
        not raise conflicts call the `replay` function to mirror the
        changes on the target.

        Return a tuple of two elements:

        - the last applied changeset, if any
        - the sequence (potentially empty!) of conflicts.
        """

        changesets = self._getUpstreamChangesets(root, sincerev)
        c = None
        conflicts = []
        for c in changesets:
            print "# Applying upstream changeset", c.revision
            
            res = self._applyChangeset(root, c)
            if res:
                conflicts.append((c, res))
                try:
                    raw_input(CONFLICTS_PROMPT % (str(c), '\n * '.join(res)))
                except KeyboardInterrupt:
                    print "INTERRUPTED BY THE USER!"
                    return c, conflicts
                
            if replay:
                replay(root, c)

            print
            
        return c, conflicts
        
    def _getUpstreamChangesets(self, root, sincerev):
        """
        Query the upstream repository about what happened on the
        sources since last sync, returning a sequence of Changesets
        instances.
        
        This method must be overridden by subclasses.
        """

        raise "%s should override this method" % self.__class__
        
    def _applyChangeset(self, root, changeset):
        """
        Do the actual work of applying the changeset to the working copy.

        Subclasses should reimplement this method performing the
        necessary steps to *merge* given `changeset`, returning a list
        with the conflicts, if any.
        """

        raise "%s should override this method" % self.__class__

    def checkoutUpstreamRevision(self, root, repository, module, revision):
        """
        Extract a working copy from a repository.

        :root: the name of the directory (that **must** exists)
               that will contain the working copy of the sources under the
               *module* subdirectory

        :repository: the address of the repository (the format depends on
                     the actual method used by the subclass)

        :module: the name of the module to extract
        
        :revision: extract that revision/branch

        Return the checked out revision.
        """

        return self._checkoutUpstreamRevision(root, repository,
                                              module, revision)
        
    def _checkoutUpstreamRevision(self, basedir, repository, module, revision):
        """
        Concretely do the checkout of the upstream revision.
        """
        
        raise "%s should override this method" % self.__class__
