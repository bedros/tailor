# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Subversion details
# :Creato:   ven 18 giu 2004 15:00:52 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

"""
This module contains supporting classes for Subversion.
"""

__docformat__ = 'reStructuredText'

from shwrap import ExternalCommand, PIPE, STDOUT, ReopenableNamedTemporaryFile
from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from target import SynchronizableTargetWorkingDir, TargetInitializationFailure
from config import ConfigurationError

def changesets_from_svnlog(log, repository, chunksize=2**15):
    from xml.sax import make_parser
    from xml.sax.handler import ContentHandler, ErrorHandler
    from changes import ChangesetEntry, Changeset
    from datetime import datetime

    def get_entry_from_path(path, module=repository.module):
        # Given the repository url of this wc, say
        #   "http://server/plone/CMFPlone/branches/Plone-2_0-branch"
        # extract the "entry" portion (a relative path) from what
        # svn log --xml says, ie
        #   "/CMFPlone/branches/Plone-2_0-branch/tests/PloneTestCase.py"
        # that is to say "tests/PloneTestCase.py"

        if path.startswith(module):
            relative = path[len(module):]
            if relative.startswith('/'):
                return relative[1:]
            else:
                return relative

        # The path is outside our tracked tree...
        repository.log.warning('Ignoring %r since it is not under %r',
                               path, module)
        return None

    class SvnXMLLogHandler(ContentHandler):
        # Map between svn action and tailor's.
        # NB: 'R', in svn parlance, means REPLACED, something other
        # system may view as a simpler ADD, taking the following as
        # the most common idiom::
        #
        #   # Rename the old file with a better name
        #   $ svn mv somefile nicer-name-scheme.py
        #
        #   # Be nice with lazy users
        #   $ echo "exec nicer-name-scheme.py" > somefile
        #
        #   # Add the wrapper with the old name
        #   $ svn add somefile
        #
        #   $ svn commit -m "Longer name for somefile"

        ACTIONSMAP = {'R': 'R', # will be ChangesetEntry.ADDED
                      'M': ChangesetEntry.UPDATED,
                      'A': ChangesetEntry.ADDED,
                      'D': ChangesetEntry.DELETED}

        def __init__(self):
            self.changesets = []
            self.current = None
            self.current_field = []
            self.renamed = {}
            self.copies = []

        def startElement(self, name, attributes):
            if name == 'logentry':
                self.current = {}
                self.current['revision'] = attributes['revision']
                self.current['entries'] = []
                self.copies = []
            elif name in ['author', 'date', 'msg']:
                self.current_field = []
            elif name == 'path':
                self.current_field = []
                if attributes.has_key('copyfrom-path'):
                    self.current_path_action = (
                        attributes['action'],
                        attributes['copyfrom-path'],
                        attributes['copyfrom-rev'])
                else:
                    self.current_path_action = attributes['action']

        def endElement(self, name):
            if name == 'logentry':
                # Sort the paths to make tests easier
                self.current['entries'].sort(lambda a,b: cmp(a.name, b.name))

                # Eliminate "useless" entries: SVN does not have atomic
                # renames, but rather uses a ADD+RM duo.
                #
                # So cycle over all entries of this patch, discarding
                # the deletion of files that were actually renamed, and
                # at the same time change related entry from ADDED to
                # RENAMED.

                # When copying a directory from another location in the
                # repository (outside the tracked tree), SVN will report files
                # below this dir that are not being committed as being
                # removed.

                # We thus need to change the action_kind for all entries
                # that are below a dir that was "copyfrom" from a path
                # outside of this module:
                #  D -> Remove entry completely (it's not going to be in here)
                #  (M,A,R) -> A

                mv_or_cp = {}
                for e in self.current['entries']:
                    if e.action_kind == e.ADDED and e.old_name is not None:
                        mv_or_cp[e.old_name] = e

                def parent_was_copied(n):
                    for p in self.copies:
                        if n.startswith(p+'/'):
                            return True
                    return False

                entries = []
                for e in self.current['entries']:
                    if e.action_kind==e.DELETED and mv_or_cp.has_key(e.name):
                        mv_or_cp[e.name].action_kind = e.RENAMED
                    elif e.action_kind=='R':
                        # In svn parlance, 'R' means Replaced: a typical
                        # scenario is
                        #   $ svn mv a.txt b.txt
                        #   $ touch a.txt
                        #   $ svn add a.txt
                        if mv_or_cp.has_key(e.name):
                            mv_or_cp[e.name].action_kind = e.RENAMED
                        e.action_kind = e.ADDED
                        entries.append(e)
                    elif parent_was_copied(e.name):
                        if e.action_kind != e.DELETED:
                            e.action_kind = e.ADDED
                            entries.append(e)
                    else:
                        entries.append(e)

                svndate = self.current['date']
                # 2004-04-16T17:12:48.000000Z
                y,m,d = map(int, svndate[:10].split('-'))
                hh,mm,ss = map(int, svndate[11:19].split(':'))
                ms = int(svndate[20:-1])
                timestamp = datetime(y, m, d, hh, mm, ss, ms)

                changeset = Changeset(self.current['revision'],
                                      timestamp,
                                      self.current.get('author'),
                                      self.current['msg'],
                                      entries)
                self.changesets.append(changeset)
                self.current = None
            elif name in ['author', 'date', 'msg']:
                self.current[name] = ''.join(self.current_field)
            elif name == 'path':
                path = ''.join(self.current_field)
                entrypath = get_entry_from_path(path)
                if entrypath:
                    entry = ChangesetEntry(entrypath)

                    if type(self.current_path_action) == type( () ):
                        self.copies.append(entry.name)
                        old = get_entry_from_path(self.current_path_action[1])
                        if old:
                            entry.action_kind = self.ACTIONSMAP[self.current_path_action[0]]
                            entry.old_name = old
                            self.renamed[entry.old_name] = True
                        else:
                            entry.action_kind = entry.ADDED
                    else:
                        entry.action_kind = self.ACTIONSMAP[self.current_path_action]

                    self.current['entries'].append(entry)

        def characters(self, data):
            self.current_field.append(data)

    parser = make_parser()
    handler = SvnXMLLogHandler()
    parser.setContentHandler(handler)
    parser.setErrorHandler(ErrorHandler())

    chunk = log.read(chunksize)
    while chunk:
        parser.feed(chunk)
        for cs in handler.changesets:
            yield cs
        handler.changesets = []
        chunk = log.read(chunksize)
    parser.close()
    for cs in handler.changesets:
        yield cs


class SvnWorkingDir(UpdatableSourceWorkingDir, SynchronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir

    def _getUpstreamChangesets(self, sincerev=None):
        if sincerev:
            sincerev = int(sincerev)
        else:
            sincerev = 0

        cmd = self.repository.command("log", "--verbose", "--xml",
                                      "--revision", "%d:HEAD" % (sincerev+1))
        svnlog = ExternalCommand(cwd=self.basedir, command=cmd)
        log = svnlog.execute('.', stdout=PIPE, TZ='UTC0')[0]

        if svnlog.exit_status:
            return []

        if self.repository.filter_badchars:
            from string import maketrans
            from cStringIO import StringIO

            # Apparently some (SVN repo contains)/(SVN server dumps) some
            # characters that are illegal in an XML stream. This was the case
            # with Twisted Matrix master repository. To be safe, we replace
            # all of them with a question mark.

            if isinstance(self.repository.filter_badchars, basestring):
                allbadchars = self.repository.filter_badchars
            else:
                allbadchars = "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09" \
                              "\x0B\x0C\x0E\x0F\x10\x11\x12\x13\x14\x15" \
                              "\x16\x17\x18\x19\x1A\x1B\x1C\x1D\x1E\x1F\x7f"

            tt = maketrans(allbadchars, "?"*len(allbadchars))
            log = StringIO(log.read().translate(tt))

        return changesets_from_svnlog(log, self.repository)

    def _applyChangeset(self, changeset):
        from time import sleep

        cmd = self.repository.command("update")
        if self.repository.ignore_externals:
            cmd.append("--ignore-externals")
        cmd.extend(["--revision", changeset.revision])
        svnup = ExternalCommand(cwd=self.basedir, command=cmd)

        retry = 0
        while True:
            out, err = svnup.execute(".", stdout=PIPE, stderr=PIPE)

            if svnup.exit_status == 1:
                retry += 1
                if retry>3:
                    break
                delay = 2**retry
                self.log.error("%s returned status %s saying\n%s",
                               str(svnup), svnup.exit_status, err.read())
                self.log.warning("Retrying in %d seconds...", delay)
                sleep(delay)
            else:
                break

        if svnup.exit_status:
            raise ChangesetApplicationFailure(
                "%s returned status %s saying\n%s" % (str(svnup),
                                                     svnup.exit_status,
                                                     err.read()))

        self.log.debug("%s updated to %s",
                       ','.join([e.name for e in changeset.entries]),
                       changeset.revision)

        result = []
        for line in out:
            if len(line)>2 and line[0] == 'C' and line[1] == ' ':
                self.log.warning("Conflict after svn update: %r", line)
                result.append(line[2:-1])

        return result

    def _checkoutUpstreamRevision(self, revision):
        """
        Concretely do the checkout of the upstream revision.
        """

        from os.path import join, exists

        # Verify that the we have the root of the repository: do that
        # iterating an "svn ls" over the hierarchy until one fails

        lastok = self.repository.repository
        if not self.repository.trust_root:
            cmd = self.repository.command("ls")
            svnls = ExternalCommand(command=cmd)

            # First verify that we have a valid repository
            svnls.execute(self.repository.repository)
            if svnls.exit_status:
                lastok = None
            else:
                # Then verify it really points to the root of the
                # repository: this is needed because later the svn log
                # parser needs to know the "offset".

                reporoot = lastok[:lastok.rfind('/')]

                # Even if it would be enough asserting that the uplevel
                # directory is not a repository, find the real root to
                # suggest it in the exception.  But don't go too far, that
                # is, stop when you hit schema://...
                while '//' in reporoot:
                    svnls.execute(reporoot)
                    if svnls.exit_status:
                        break
                    lastok = reporoot
                    reporoot = reporoot[:reporoot.rfind('/')]

        if lastok is None:
            raise ConfigurationError("%r is not the root of a svn repository." %
                                     self.repository.repository)
        elif lastok <> self.repository.repository:
            module = self.repository.repository[len(lastok):]
            module += self.repository.module
            raise ConfigurationError("Non-root svn repository %r. "
                                     "Please specify that as 'repository=%s' "
                                     "and 'module=%s'." %
                                     (self.repository.repository,
                                      lastok, module.rstrip('/')))

        if revision == 'INITIAL':
            initial = True
            cmd = self.repository.command("log", "--verbose", "--xml",
                                          "--stop-on-copy",
                                          "--revision", "1:HEAD")
            if self.repository.use_limit:
                cmd.extend(["--limit", "1"])
            svnlog = ExternalCommand(command=cmd)
            out, err = svnlog.execute("%s%s" % (self.repository.repository,
                                                self.repository.module),
                                      stdout=PIPE, stderr=PIPE)

            if svnlog.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying\n%s" %
                    (str(svnlog), svnlog.exit_status, err.read()))

            csets = changesets_from_svnlog(out, self.repository)
            last = csets.next()
            revision = last.revision
        else:
            initial = False

        if not exists(join(self.basedir, '.svn')):
            self.log.debug("Checking out a working copy")

            cmd = self.repository.command("co", "--quiet")
            if self.repository.ignore_externals:
                cmd.append("--ignore-externals")
            cmd.extend(["--revision", revision])
            svnco = ExternalCommand(command=cmd)

            out, err = svnco.execute("%s%s" % (self.repository.repository,
                                               self.repository.module),
                                     self.basedir, stdout=PIPE, stderr=PIPE)
            if svnco.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %s saying\n%s" % (str(svnco),
                                                         svnco.exit_status,
                                                         err.read()))
        else:
            self.log.debug("%r already exists, assuming it's "
                           "a svn working dir", self.basedir)

        if not initial:
            if revision=='HEAD':
                revision = 'COMMITTED'
            cmd = self.repository.command("log", "--verbose", "--xml",
                                          "--revision", revision)
            svnlog = ExternalCommand(cwd=self.basedir, command=cmd)
            out, err = svnlog.execute(stdout=PIPE, stderr=PIPE)

            if svnlog.exit_status:
                raise TargetInitializationFailure(
                    "%s returned status %d saying\n%s" %
                    (str(svnlog), svnlog.exit_status, err.read()))

            csets = changesets_from_svnlog(out, self.repository)
            last = csets.next()

        self.log.debug("Working copy up to svn revision %s", last.revision)

        return last

    ## SynchronizableTargetWorkingDir

    def _addPathnames(self, names):
        """
        Add some new filesystem objects.
        """

        cmd = self.repository.command("add", "--quiet", "--no-auto-props",
                                      "--non-recursive")
        ExternalCommand(cwd=self.basedir, command=cmd).execute(names)

    def _commit(self, date, author, patchname, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        from re import search

        encode = self.repository.encode

        logmessage = []
        if patchname:
            logmessage.append(patchname)
        if changelog:
            logmessage.append(changelog)

        # If we cannot use propset, fall back to old behaviour of
        # appending these info to the changelog

        if not self.USE_PROPSET:
            logmessage.append('')
            logmessage.append('Original author: %s' % encode(author))
            logmessage.append('Date: %s' % date)

        rontf = ReopenableNamedTemporaryFile('svn', 'tailor')
        log = open(rontf.name, "w")
        log.write(encode('\n'.join(logmessage)))
        log.close()

        cmd = self.repository.command("commit", "--file", rontf.name)
        commit = ExternalCommand(cwd=self.basedir, command=cmd)

        if not entries:
            entries = ['.']

        out, err = commit.execute(entries, stdout=PIPE, stderr=PIPE)

        if commit.exit_status:
            raise ChangesetApplicationFailure("%s returned status %d saying\n%s"
                                              % (str(commit),
                                                 commit.exit_status,
                                                 err.read()))
        line = out.readline()
        if not line:
            # svn did not find anything to commit
            return

        # Assume svn output the revision number in the last output line
        while line:
            lastline = line
            line = out.readline()
        revno = search('\d+', lastline)
        if revno is None:
            out.seek(0)
            raise ChangesetApplicationFailure("%s wrote unrecognizable "
                                              "revision number:\n%s" %
                                              (str(commit), out.read()))
        revision = revno.group(0)

        if self.USE_PROPSET:
            cmd = self.repository.command("propset", "%(propname)s",
                                          "--quiet", "--revprop",
                                          "--revision", revision)
            propset = ExternalCommand(cwd=self.basedir, command=cmd)

            propset.execute(date.isoformat()+".000000Z", propname='svn:date')
            propset.execute(encode(author), propname='svn:author')

        cmd = self.repository.command("update", "--quiet")
        if self.repository.ignore_externals:
            cmd.append("--ignore-externals")
        cmd.extend(["--revision", revision])

        ExternalCommand(cwd=self.basedir, command=cmd).execute()

    def _removePathnames(self, names):
        """
        Remove some filesystem objects.
        """

        cmd = self.repository.command("remove", "--quiet", "--force")
        remove = ExternalCommand(cwd=self.basedir, command=cmd)
        remove.execute(names)

    def _renamePathname(self, oldname, newname):
        """
        Rename a filesystem object.
        """

        from os import rename, walk, remove
        from os.path import join, isdir, exists

        # --force in case the file has been changed and moved in one revision
        cmd = self.repository.command("mv", "--quiet", "--force")
        # Subversion does not seem to allow
        #   $ mv a.txt b.txt
        #   $ svn mv a.txt b.txt
        # Here we are in this situation, since upstream VCS already
        # moved the item.
        # It may be better to let subversion do the move itself. For one thing,
        # svn's cp+rm is different from rm+add (cp preserves history).
        unmoved = False
        oldpath = join(self.basedir, oldname)
        newpath = join(self.basedir, newname)
        if not exists(oldpath):
            try:
                rename(newpath, oldpath)
            except OSError:
                self.log.critical('Cannot rename %r back to %r',
                                  newpath, oldpath)
                raise
            unmoved = True
        move = ExternalCommand(cwd=self.basedir, command=cmd)
        out, err = move.execute(oldname, newname, stdout=PIPE, stderr=PIPE)
        if move.exit_status:
            if unmoved:
                rename(oldpath, newpath)
            raise ChangesetApplicationFailure("%s returned status %d saying\n%s"
                                              % (str(move), move.exit_status,
                                                 err.read()))

    def __createRepository(self, target_repository, target_module):
        """
        Create a local repository.
        """

        from os.path import join
        from sys import platform

        assert target_repository.startswith('file:///')
        repodir = target_repository[7:]
        cmd = self.repository.command("create", "--fs-type", "fsfs",
                                      svnadmin=True)
        svnadmin = ExternalCommand(command=cmd)
        svnadmin.execute(repodir)

        if svnadmin.exit_status:
            raise TargetInitializationFailure("Was not able to create a 'fsfs' "
                                              "svn repository at %r" %
                                              target_repository)
        if self.USE_PROPSET:
            hookname = join(repodir, 'hooks', 'pre-revprop-change')
            if platform == 'win32':
                hookname += '.bat'
            prehook = open(hookname, 'wU')
            if platform <> 'win32':
                prehook.write('#!/bin/sh\n')
            prehook.write('exit 0\n')
            prehook.close()
            if platform <> 'win32':
                from os import chmod
                chmod(hookname, 0755)

        if target_module and target_module <> '/':
            cmd = self.repository.command("mkdir", "-m",
                                          "This directory will host the "
                                          "upstream sources")
            svnmkdir = ExternalCommand(command=cmd)
            svnmkdir.execute(target_repository + target_module)
            if svnmkdir.exit_status:
                raise TargetInitializationFailure("Was not able to create the "
                                                  "module %r, maybe more than "
                                                  "one level directory?" %
                                                  target_module)

    def _prepareTargetRepository(self):
        """
        Check for target repository existence, eventually create it.
        """

        if not self.repository.repository:
            return

        # Verify the existence of repository by listing its root
        cmd = self.repository.command("ls")
        svnls = ExternalCommand(command=cmd)
        svnls.execute(self.repository.repository)

        if svnls.exit_status:
            if self.repository.repository.startswith('file:///'):
                self.__createRepository(self.repository.repository,
                                        self.repository.module)
            else:
                raise TargetInitializationFailure("%r does not exist and "
                                                  "cannot be created since "
                                                  "it's not a local (file:///) "
                                                  "repository" %
                                                  self.repository.repository)

    def _prepareWorkingDirectory(self, source_repo):
        """
        Checkout a working copy of the target SVN repository.
        """

        from os.path import join, exists

        if not self.repository.repository or exists(join(self.basedir, '.svn')):
            return

        cmd = self.repository.command("co", "--quiet")
        if self.repository.ignore_externals:
            cmd.append("--ignore-externals")

        svnco = ExternalCommand(command=cmd)
        svnco.execute("%s%s" % (self.repository.repository,
                                self.repository.module), self.basedir)

    def _initializeWorkingDir(self):
        """
        Add the given directory to an already existing svn working tree.
        """

        from os.path import exists, join

        if not exists(join(self.basedir, '.svn')):
            raise TargetInitializationFailure("'%s' needs to be an SVN working copy already under SVN" % self.basedir)

        SynchronizableTargetWorkingDir._initializeWorkingDir(self)
