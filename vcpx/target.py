#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Syncable targets
# :Creato:   ven 04 giu 2004 00:27:07 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# 

"""
Syncronizable targets are the simplest abstract wrappers around a
working directory under two different version control systems.
"""

__docformat__ = 'reStructuredText'

PATCH_AUTHOR = "tailor@localhost"

class SyncronizableTargetWorkingDir(object):
    """
    This is an abstract working dir usable as a *shadow* of another
    kind of VC, sharing the same working directory.

    Most interesting entry points are:

    replayChangeset
        to replay an already applied changeset, to mimic the actions
        performed by the upstream VC system on the tree such as
        renames, deletions and adds.  This is an useful argument to
        feed as `replay` to `applyUpstreamChangesets`

    initializeNewWorkingDir
        to initialize a pristine working directory tree under this VC
        system, possibly extracted under a different kind of VC
    
    Subclasses MUST override at least the _underscoredMethods.
    """

    def replayChangeset(self, root, changeset):
        """
        Do whatever is needed to replay the changes under the target
        VC, to register the already applied (under the other VC)
        changeset.
        """

        self._replayChangeset(root, changeset)
        
        remark = 'Upstream changeset %s - %s' % (changeset.revision,
                                                 changeset.date)
        changelog = changeset.log
        entries = [e.name for e in changeset.entries]
        self._commit(root, changeset.date, changeset.author,
                     remark, changelog, entries)

    def _replayChangeset(self, root, changeset):
        """
        Replicate the actions performed by the changeset on the tree of
        files.
        """
        
        for e in changeset.entries:
            if e.action_kind == e.RENAMED:
                self._renameEntry(root, e.old_name, e.name)
            elif e.action_kind == e.ADDED:
                self._addEntry(root, e.name)
            elif e.action_kind == e.DELETED:
                self._removeEntry(root, e.name)
        
    def _addEntry(self, root, entry):
        """
        Add a new entry, maybe registering the directory as well.
        """

        raise "%s should override this method" % self.__class__

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """
        
        raise "%s should override this method" % self.__class__
        
    def _removeEntry(self, root, entry):
        """
        Remove an entry.
        """

        raise "%s should override this method" % self.__class__

    def _renameEntry(self, root, oldentry, newentry):
        """
        Rename an entry.
        """

        raise "%s should override this method" % self.__class__

    def initializeNewWorkingDir(self, root, repository, revision):
        """
        Initialize a new working directory, just extracted under
        some other VC system, importing everything's there.
        """

        from datetime import datetime

        now = datetime.now()
        self._initializeWorkingDir(root)
        self._commit(root, now, PATCH_AUTHOR,
                     'Tailorization of %s@%s' % (repository, revision))

    def _initializeWorkingDir(self, root, addentry=None):
        """
        Assuming the `root` directory is a new working copy extracted
        from some VC repository, add it and all its content to the
        target repository.

        This implementation first runs the given `addentry`
        *SystemCommand* on the `root` directory, then it walks down
        the `root` tree executing the same command on each entry
        excepted the usual VC-specific control directories such as
        ``.svn``, ``_darcs`` or ``CVS``.

        If this does make sense, subclasses should just call this
        method with the right `addentry` command.
        """

        assert addentry, "Subclass should have specified something as addentry"
        
        from os.path import split
        from os import walk

        basedir,wdir = split(root)
        c = addentry(working_dir=basedir)
        c(entry=repr(wdir))

        for dir, subdirs, files in walk(root):
            for excd in ['.svn', '_darcs', 'CVS']:
                if excd in subdirs:
                    subdirs.remove(excd)

            c = addentry(working_dir=dir)
            for d in subdirs+files:
                c(entry=repr(d))

