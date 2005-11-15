# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Mercurial native backend
# :Creato:   dom 11 set 2005 22:58:38 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
#            Brendan Cully <brendan@kublai.com>
# :Licenza:  GNU General Public License
#

"""
This module implements the backends for Mercurial, using its native API
instead of thru the command line.
"""

__docformat__ = 'reStructuredText'

from source import UpdatableSourceWorkingDir
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from mercurial import ui, hg, commands, util
import os

class HglibWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):
    # UpdatableSourceWorkingDir
    def _checkoutUpstreamRevision(self, revision):
        """
        Initial checkout (hg clone)
        """

        self._getUI()
        # We have to clone the entire repository to be able to pull from it
        # later. So a partial checkout is a full clone followed by an update
        # directly to the desired revision.

        # Hg won't check out into an existing directory
        checkoutdir = os.path.join(self.basedir,".hgtmp")
        commands.clone(self._ui, self.repository.repository, checkoutdir,
                       noupdate=True, ssh=None, remotecmd=None)
        os.rename(os.path.join(checkoutdir, ".hg"),
                  os.path.join(self.basedir,".hg"))
        os.rmdir(checkoutdir)

        repo = self._getRepo()
        node = self._getNode(repo, revision)

        self.log.info('Extracting revision %s from %s into %s',
                      revision, self.repository.repository, self.basedir)
        repo.update(node)

        return self._changesetForRevision(repo, revision)

    def _getUpstreamChangesets(self, sincerev):
        """Fetch new changesets from the source"""
        ui = self._getUI()
        repo = self._getRepo()

        commands.pull(ui, repo, "default", ssh=None, remotecmd=None, update=None)

        from mercurial.node import bin
        for rev in xrange(repo.changelog.rev(bin(sincerev)) + 1, repo.changelog.count()):
            yield self._changesetForRevision(repo, str(rev))

    def _applyChangeset(self, changeset):
        repo = self._getRepo()
        node = self._getNode(repo, changeset.revision)

        return repo.update(node)

    def _changesetForRevision(self, repo, revision):
        from changes import Changeset, ChangesetEntry
        from datetime import datetime

        entries = []
        node = self._getNode(repo, revision)
        parents = repo.changelog.parents(node)
        (manifest, user, date, files, message) = repo.changelog.read(node)

        # Different targets seem to handle the TZ differently. It looks like
        # darcs may be the most correct.
        (dt, tz) = date.split(' ')
        date = datetime.fromtimestamp(int(dt) + int(tz))

        manifest = repo.manifest.read(manifest)

        # To find adds, we get the manifests of any parents. If a file doesn't
        # occur there, it's new.
        pms = {}
        for parent in repo.changelog.parents(node):
            pms.update(repo.manifest.read(repo.changelog.read(parent)[0]))

        # if files contains only '.hgtags', this is probably a tag cset.
        # Tailor appears to only support tagging the current version, so only
        # pass on tags that are for the immediate parents of the current node
        tags = None
        if files == ['.hgtags']:
            tags = [tag for (tag, tagnode) in repo.tags().iteritems()
                    if tagnode in parents]
            # Since this is a tag, the parent manifest contains everything.
            # The only question is whether or not .hgtags existed before
            if pms.has_key('.hgtags'):
                pms = {'.hgtags': pms['.hgtags']}
            else:
                pms = {}

        # Every time we find a file in the current manifest, we pop it from the parents.
        # Anything left over in parents is a deleted file.
        for f in files:
            e = ChangesetEntry(f)
            # find renames
            fl = repo.file(f)
            oldname = fl.renamed(manifest[f])
            if oldname:
                e.action_kind = ChangesetEntry.RENAMED
                e.old_name = oldname[0]
                pms.pop(oldname[0])
            else:
                try:
                    del pms[f]
                    e.action_kind = ChangesetEntry.UPDATED
                except KeyError:
                    e.action_kind = ChangesetEntry.ADDED

            entries.append(e)

        for df in pms.iterkeys():
            e = ChangesetEntry(df)
            e.action_kind = ChangesetEntry.DELETED

        from mercurial.node import hex
        revision = hex(node)
        return Changeset(revision, date, user, message, entries, tags=tags)

    def _getUI(self):
        try:
            return self._ui
        except AttributeError:
            project = self.repository.projectref()
            self._ui = ui.ui(project.verbose,
                             project.config.get(self.repository.name,
                                                'debug', False),
                             not project.verbose, False)
            return self._ui

    def _getRepo(self):
        try:
            return self._hg
        except AttributeError:
            ui = self._getUI()
            self._hg = hg.repository(ui=ui, path=self.basedir, create=False)
            return self._hg

    def _getNode(self, repo, revision):
        """Convert a tailor revision ID into an hg node"""
        if revision == "HEAD":
            node = repo.changelog.tip()
        else:
            if revision == "INITIAL":
                rev = "0"
            else:
                rev = revision
            node = repo.changelog.lookup(rev)

        return node

    def _normalizeEntryPaths(self, entry):
        """
        Normalize the name and old_name of an entry.

        This implementation uses ``mercurial.util.normpath()``, since
        at this level hg is expecting UNIX style pathnames, with
        forward slash"/" as separator, also under insane operating systems.
        """

        entry.name = util.normpath(entry.name)
        if entry.old_name:
            entry.old_name = util.normpath(entry.old_name)

    def _addPathnames(self, names):
        from os.path import join, isdir, normpath

        notdirs = [n for n in names
                   if not isdir(join(self.basedir, normpath(n)))]
        if notdirs:
            self._hg.add(notdirs)

    def _commit(self, date, author, patchname, changelog=None, names=None):
        from time import mktime

        encoding = self.repository.encoding

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)
        if logmessage:
            logmessage = '\n'.join(logmessage).encode(encoding)
        else:
            logmessage = "Empty changelog"
        self._hg.commit(names and [n.encode(encoding) for n in names] or [],
                        logmessage, author.encode(encoding),
                        "%d 0" % mktime(date.timetuple()))

    def _removePathnames(self, names):
        """Remove a sequence of entries"""

        from os.path import join, isdir, normpath

        notdirs = [n for n in names
                   if not isdir(join(self.basedir, normpath(n)))]
        if notdirs:
            self._hg.remove(notdirs)

    def _renamePathname(self, oldname, newname):
        """Rename an entry"""

        from os.path import join, isdir, normpath

        if isdir(join(self.basedir, normpath(newname))):
            # Given lack of support for directories in current HG,
            # loop over all files under the old directory and
            # do a copy on them.
            for src, oldpath in self._hg.dirstate.walk(oldname):
                tail = oldpath[len(oldname)+2:]
                self._hg.copy(oldpath, join(newname, tail))
                self._hg.remove([oldpath])
        else:
            self._hg.copy(oldname, newname)
            self._hg.remove([oldname])

    def _prepareTargetRepository(self):
        """
        Create the base directory if it doesn't exist, and the
        repository as well in the new working directory.
        """

        from os.path import join, exists

        self._getUI()

        if exists(join(self.basedir, self.repository.METADIR)):
            create = 0
        else:
            create = 1
        self._hg = hg.repository(ui=self._ui, path=self.basedir, create=create)

    def _prepareWorkingDirectory(self, source_repo):
        """
        Create the .hgignore.
        """

        from os.path import join
        from re import escape
        from dualwd import IGNORED_METADIRS

        # Create the .hgignore file, that contains a regexp per line
        # with all known VCs metadirs to be skipped.
        ignore = open(join(self.basedir, '.hgignore'), 'w')
        ignore.write('\n'.join(['(^|/)%s($|/)' % escape(md)
                                for md in IGNORED_METADIRS]))
        ignore.write('\n')
        if self.logfile.startswith(self.basedir):
            ignore.write('^')
            ignore.write(self.logfile[len(self.basedir)+1:])
            ignore.write('$\n')
        if self.state_file.filename.startswith(self.basedir):
            sfrelname = self.state_file.filename[len(self.basedir)+1:]
            ignore.write('^')
            ignore.write(sfrelname)
            ignore.write('$\n')
            ignore.write('^')
            ignore.write(sfrelname+'.old')
            ignore.write('$\n')
            ignore.write('^')
            ignore.write(sfrelname+'.journal')
            ignore.write('$\n')
        ignore.close()

    def _initializeWorkingDir(self):
        commands.add(self._ui, self._hg, self.basedir)
