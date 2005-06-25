# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Syncable targets
# :Creato:   ven 04 giu 2004 00:27:07 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 

"""
Syncronizable targets are the simplest abstract wrappers around a
working directory under two different version control systems.
"""

__docformat__ = 'reStructuredText'

import socket
from shwrap import shrepr

HOST = socket.getfqdn()
AUTHOR = "tailor"
BOOTSTRAP_PATCHNAME = 'Tailorization of %s'
BOOTSTRAP_CHANGELOG = """\
Import of the upstream sources from

  Repository: %(repository)s
  Module:     %(module)s
  Revision:   %(revision)s
"""

class TargetInitializationFailure(Exception):
    "Failure initializing the target VCS"
    
    pass

class SyncronizableTargetWorkingDir(object):
    """
    This is an abstract working dir usable as a *shadow* of another
    kind of VC, sharing the same working directory.

    Most interesting entry points are:

    replayChangeset
        to replay an already applied changeset, to mimic the actions
        performed by the upstream VC system on the tree such as
        renames, deletions and adds.  This is an useful argument to
        feed as ``replay`` to ``applyUpstreamChangesets``

    initializeNewWorkingDir
        to initialize a pristine working directory tree under this VC
        system, possibly extracted under a different kind of VC
    
    Subclasses MUST override at least the _underscoredMethods.
    """

    PATCH_NAME_FORMAT = '%(module)s: changeset %(revision)s'
    """
    The format string used to compute the patch name, used by underlying VCS.
    """

    REMOVE_FIRST_LOG_LINE = False
    """
    When true, remove the first line from the upstream changelog.
    """
    
    def replayChangeset(self, root, module, changeset,
                        delayed_commit=False, logger=None):
        """
        Do whatever is needed to replay the changes under the target
        VC, to register the already applied (under the other VC)
        changeset.

        If ``delayed_commit`` is not True, the changeset is committed
        to the target VC right after a successful application; otherwise
        the various information get registered and will be reused later,
        by commitDelayedChangesets().
        """

        try:
            self._replayChangeset(root, changeset, logger)
        except:
            if logger: logger.critical(str(changeset))
            raise
        
        if delayed_commit:
            self.__registerAppliedChangeset(changeset)
        else:
            if changeset.log == '':
                firstlogline = 'Empty log message'
                remaininglog = ''
            else:
                loglines = changeset.log.split('\n')
                if len(loglines)>1:
                    firstlogline = loglines[0]
                    remaininglog = '\n'.join(loglines[1:])
                else:
                    firstlogline = changeset.log
                    remaininglog = ''
                    
            remark = self.PATCH_NAME_FORMAT % {
                'module': module,
                'revision': changeset.revision,
                'author': changeset.author,
                'date': changeset.date,
                'firstlogline': firstlogline,
                'remaininglog': remaininglog}
            if self.REMOVE_FIRST_LOG_LINE:
                changelog = remaininglog
            else:
                changelog = changeset.log
            entries = self._getCommitEntries(changeset)
            self._commit(root, changeset.date, changeset.author,
                         remark, changelog, entries)

    def commitDelayedChangesets(self, root, concatenate_logs=True):
        """
        If there are changesets pending to be committed, do a single
        commit of all changed entries.

        With ``concatenate_logs`` there's control over the folded
        changesets message log: if True every changelog is appended in
        order of application, otherwise it will contain just the name
        of the patches.
        """

        from datetime import datetime
        
        if not hasattr(self, '_registered_cs'):
            return

        mindate = maxdate = None
        combined_entries = {}
        combined_log = []
        combined_authors = {}
        for cs in self._registered_cs:
            if not mindate or mindate>cs.date:
                mindate = cs.date
            if not maxdate or maxdate<cs.date:
                maxdate = cs.date

            if concatenate_logs:
                msg = 'changeset %s by %s' % (cs.revision, cs.author)
                combined_log.append(msg)
                combined_log.append('=' * len(msg))
                combined_log.append(cs.log)
            else:
                combined_log.append('* changeset %s by %s' % (cs.revision,
                                                              cs.author))
            combined_authors[cs.author] = True
            
            for e in self._getCommitEntries(cs):
                combined_entries[e] = True

        authors = ', '.join(combined_authors.keys())
        remark = (self.PATCH_NAME_FORMAT or
                  'Merged %(nchangesets) changesets '
                  'from %(mindate)s to %(maxdate)s') % {
            'module': module,
            'nchangesets': len(self._registered_cs),
            'authors': authors,
            'mindate': mindate,
            'maxdate': maxdate}
        changelog = '\n'.join(combined_log)
        entries = combined_entries.keys()
        self._commit(root, datetime.now(), authors,
                         remark, changelog, entries)

    def _getCommitEntries(self, changeset):
        """
        Extract the names of the entries for the commit phase.
        """
        
        return [e.name for e in changeset.entries]
        
    def _replayChangeset(self, root, changeset, logger):
        """
        Replicate the actions performed by the changeset on the tree of
        files.
        """

        from os.path import join, isdir
        
        added = changeset.addedEntries()
        addeddirs = []
        addedfiles = []
        for e in added:
            if isdir(join(root, e.name)):
                addeddirs.append(e)
            else:
                addedfiles.append(e)
        renamed = changeset.renamedEntries()
        removed = changeset.removedEntries()

        # Sort added dirs, to be sure that /root/addedDir/ comes before
        # /root/addedDir/addedSubdir
        addeddirs.sort(lambda x,y: cmp(x.name, y.name))
        
        # Sort removes in reverse order, to delete directories after
        # their entries.
        removed.sort(lambda x,y: cmp(y.name, x.name))

        # First of all, add each subdirectory, since they may be targets
        # of succeeding operations.
        
        if addeddirs: self._addEntries(root, addeddirs)

        # Then process the actual files
        
        if renamed: self._renameEntries(root, renamed)
        if removed: self._removeEntries(root, removed)
        if addedfiles: self._addEntries(root, addedfiles)

        # Finally, deal with "copied" directories. The simple way is
        # executing an _addSubtree on each of them, evenif this may
        # cause "warnings" on items just moved/added above...

        while addeddirs:
            subdir = addeddirs.pop(0).name
            self._addSubtree(root, subdir)
            addeddirs = [d for d in addeddirs if not d.name.startswith(subdir)]

    def __registerAppliedChangeset(self, changeset):
        """
        Remember about an already applied but not committed changeset,
        to be done later.
        """
        
        if not hasattr(self, '_registered_cs'):
            self._registered_cs = []

        self._registered_cs.append(changeset)

    def _addEntries(self, root, entries):
        """
        Add a sequence of entries
        """

        self._addPathnames(root, [e.name for e in entries])
        
    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        raise "%s should override this method" % self.__class__

    def _addSubtree(self, root, subdir):
        """
        Add a whole subtree.

        This implementation crawl down the whole subtree, adding
        entries (subdirs, skipping the usual VC-specific control
        directories such as ``.svn``, ``_darcs`` or ``CVS``, and
        files).

        Subclasses may use a better way, if the backend implements
        a recursive add that skips the various metadata directories.
        """
        
        from os.path import join
        from os import walk

        if subdir<>'.':
            self._addPathnames(root, [subdir])

        for dir, subdirs, files in walk(join(root, subdir)):
            for excd in ['.svn', '_darcs', 'CVS', '.cdv', 'MT']:
                if excd in subdirs:
                    subdirs.remove(excd)

            # Uhm, is this really desiderable?
            for excf in ['tailor.info', 'tailor.log']:
                if excf in files:
                    files.remove(excf)

            if subdirs or files:
                self._addPathnames(dir, subdirs + files)

    def _commit(self, root, date, author, remark,
                changelog=None, entries=None):
        """
        Commit the changeset.
        """
        
        raise "%s should override this method" % self.__class__

    def _removeEntries(self, root, entries):
        """
        Remove a sequence of entries.
        """

        self._removePathnames(root, [e.name for e in entries])
            
    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        raise "%s should override this method" % self.__class__

    def _renameEntries(self, root, entries):
        """
        Rename a sequence of entries.
        """
        
        for e in entries:
            self._renamePathname(root, e.old_name, e.name)
        
    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object to some other name/location.
        """

        raise "%s should override this method" % self.__class__

    def initializeNewWorkingDir(self, root, repository, module, subdir, revision):
        """
        Initialize a new working directory, just extracted from
        some other VC system, importing everything's there.
        """

        from datetime import datetime

        now = datetime.now()
        self._initializeWorkingDir(root, repository, module, subdir)
        patchname = BOOTSTRAP_PATCHNAME % module
        changelog = BOOTSTRAP_CHANGELOG % locals()
        self._commit(root, now, '%s@%s' % (AUTHOR, HOST), patchname, changelog,
                     entries=[subdir])

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Assuming the ``root`` directory contains a working copy ``module``
        extracted from some VC repository, add it and all its content
        to the target repository.

        This implementation recursively add every file in the subtree.
        Subclasses should override this method doing whatever is
        appropriate for the backend.
        """

        self._addSubtree(root, subdir)
