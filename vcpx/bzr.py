# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- bazaar-ng support using the bzrlib instead of the frontend
# :Creato:   Fri Aug 19 01:06:08 CEST 2005
# :Autore:   Johan Rydberg <jrydberg@gnu.org>
#            Jelmer Vernooij <jelmer@samba.org>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Bazaar-NG.
"""

__docformat__ = 'reStructuredText'

from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from bzrlib.branch import Branch

class BzrWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    ## UpdatableSourceWorkingDir

    def _changesetFromRevision(self, parent, revision):
        """
        Generate changeset for the given Bzr revision
        """
        from changes import ChangesetEntry, Changeset
        from datetime import datetime
        r = parent.get_revision(revision)

        deltatree = parent.get_revision_delta(parent.revision_id_to_revno(revision))
        entries = []

        for delta in deltatree.added:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.ADDED
            entries.append(e)

        for delta in deltatree.removed:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.DELETED
            entries.append(e)

        for delta in deltatree.renamed:
            e = ChangesetEntry(delta[1])
            e.action_kind = ChangesetEntry.RENAMED
            e.old_name = delta[0]
            entries.append(e)

        for delta in deltatree.modified:
            e = ChangesetEntry(delta[0])
            e.action_kind = ChangesetEntry.UPDATED
            entries.append(e)

        return Changeset(r.revision_id,
                              datetime.fromtimestamp(r.timestamp),
                              r.committer,
                              r.message,
                              entries)

    def _getUpstreamChangesets(self, sincerev):
        """
        See what other revisions exist upstream and return them
        """
        parent = Branch.open(self.repository.repository)

        revisions = self._b.missing_revisions(parent)

        for ri in revisions:
            yield self._changesetFromRevision(parent, ri)

    def _applyChangeset(self, changeset):
        """
        Apply given remote revision to workingdir
        """
        from bzrlib.merge import merge

        oldrevno = self._b.revno()
        self._b.append_revision(changeset.revision)
        merge((self.basedir, -1), (self.basedir, oldrevno),
              check_clean=False, this_dir=self.basedir)
        return [] # No conflicts for now

    def _checkoutUpstreamRevision(self, revision):
        """
        Initial checkout, equivalent of 'bzr branch -r ... '
        """
        from bzrlib.clone import copy_branch

        parent = Branch.open(self.repository.repository)

        if revision == "INITIAL":
            revid = parent.get_rev_id(1)
        elif revision == "HEAD":
            revid = None
        else:
            revid = revision

        self._b = copy_branch(parent, self.basedir, revid)

        return self._changesetFromRevision(parent, revid)

    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, entries):
        # This method may get invoked several times with the same
        # entries; and Branch.add complains if a file is already
        # versioned.  So go through the list and sort out entries that
        # is already versioned, since there is no need to add them.
        # Do not try to catch any errors from Branch.add, since the
        # they are _real_ errors.
        new_entries = []
        for e in entries:
            if not self._b.inventory.has_filename(e):
                new_entries.extend([e])

        if len(new_entries) == 0:
            return
        self._b.add(new_entries)

    def _addSubtree(self, subdir):
        """
        Add a whole subtree.

        Use smart_add_branch() to add a whole new subtree to the
        repository.
        """

        from os.path import join
        from bzrlib.add import smart_add_branch

        smart_add_branch(self._b, [join(self.basedir, subdir)], recurse=True)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        from time import mktime
        from binascii import hexlify
        from re import search
        from bzrlib.osutils import compact_date, rand_bytes

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        if logmessage:
            logmessage = '\n'.join(logmessage)
        else:
            logmessage = "Empty changelog"
        timestamp = int(mktime(date.timetuple()))

        # Guess sane email address
        email = search("<(.*@.*)>", author)
        if email:
            email = email.group(1)
        else:
            email = author

        revision_id = "%s-%s-%s" % (email, compact_date(timestamp),
                                    hexlify(rand_bytes(8)))
        self._b.commit(logmessage, committer=author,
                       specific_files=entries, rev_id=revision_id,
                       verbose=self.repository.project.verbose,
                       timestamp=timestamp)

    def _removePathnames(self, entries):
        """Remove a sequence of entries"""

        self._b.remove(entries)

    def _renamePathname(self, oldentry, newentry):
        """Rename an entry"""

        from os import rename
        from os.path import join

        # bzr does the rename itself as well
        rename(join(self.basedir, newentry), join(self.basedir, oldentry))

        self._b.rename_one(oldentry, newentry)

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory.
        """

        from os.path import join, exists, split
        from bzrlib import IGNORE_FILENAME

        if not exists(join(self.basedir, self.repository.METADIR)):
            ignored = []

            # Omit our own log...
            logfile = self.repository.project.logfile
            dir, file = split(logfile)
            if dir == self.basedir:
                ignored.append(file)

            # ... and state file
            sfname = self.repository.project.state_file.filename
            dir, file = split(sfname)
            if dir == self.basedir:
                ignored.append(file)
                ignored.append(file+'.journal')

            if ignored:
                bzrignore = open(join(self.basedir, IGNORE_FILENAME), 'wU')
                bzrignore.write('\n'.join(ignored))

            self._b = Branch.initialize(self.basedir)
        else:
            self._b = Branch.open(self.basedir)
