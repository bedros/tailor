#! /usr/bin/python
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

from shwrap import SystemCommand, shrepr, ReopenableNamedTemporaryFile
from source import UpdatableSourceWorkingDir, \
     ChangesetApplicationFailure, GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure


class SvnUpdate(SystemCommand):
    COMMAND = "svn update --revision %(revision)s %(entry)s"


class SvnInfo(SystemCommand):
    COMMAND = "LANG= svn info %(entry)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        output = SystemCommand.__call__(self, output=True,
                                        dry_run=dry_run,
                                        **kwargs)
        res = {}
        for l in output:
            l = l[:-1]
            if l:
                key, value = l.split(':', 1)
                res[key] = value[1:]
        return res

                 
class SvnLog(SystemCommand):
    COMMAND = "TZ=UTC svn log %(quiet)s %(xml)s --revision %(startrev)s:%(endrev)s %(entry)s > %(tempfilename)s 2>&1"
    
    def __call__(self, output=None, dry_run=False, **kwargs):      
        quiet = kwargs.get('quiet', True)
        if quiet == True:
            kwargs['quiet'] = '--quiet'
        elif quiet == False:
            kwargs['quiet'] = ''
            
        xml = kwargs.get('xml', False)
        if xml:
            kwargs['xml'] = '--xml'
            output = True
        else:
            kwargs['xml'] = ''

        startrev = kwargs.get('startrev')
        if not startrev:
            kwargs['startrev'] = 'BASE'

        endrev = kwargs.get('endrev')
        if not endrev:
            kwargs['endrev'] = 'HEAD'

        self.rontf = ReopenableNamedTemporaryFile('svn', 'tailor')
        logfn = kwargs['tempfilename'] = self.rontf.name
        
        SystemCommand.__call__(self, output=False, dry_run=dry_run, **kwargs)

        return open(logfn)

class SvnCommit(SystemCommand):
    COMMAND = "svn commit --quiet --file %(logfile)s %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        logfile = kwargs.get('logfile')
        rontf = ReopenableNamedTemporaryFile('svn', 'tailor')
        if not logfile:
            logmessage = kwargs.get('logmessage')
            if logmessage:
                log = open(rontf.name, "w")
                log.write(logmessage)
                log.close()            
            kwargs['logfile'] = rontf.name
        
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)


class SvnRemove(SystemCommand):
    COMMAND = "svn remove --quiet --force %(entry)s"


class SvnMv(SystemCommand):
    COMMAND = "svn mv --quiet %(old)s %(new)s"

    
class SvnCheckout(SystemCommand):
    COMMAND = "svn co --revision %(revision)s %(repository)s%(module)s %(wc)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        module = kwargs.get('module')
        if module:
            module = '/%s' % module
        else:
            module = ''
        kwargs['module'] = module
        return SystemCommand.__call__(self, output=output,
                                      dry_run=dry_run, **kwargs)


def changesets_from_svnlog(log, url, repository, module):
    from xml.sax import parseString
    from xml.sax.handler import ContentHandler
    from changes import ChangesetEntry, Changeset
    from datetime import datetime

    def get_entry_from_path(path, module=module):
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
            
        def startElement(self, name, attributes):
            if name == 'logentry':
                self.current = {}
                self.current['revision'] = attributes['revision']
                self.current['entries'] = []
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

                mv_or_cp = {}
                for e in self.current['entries']:
                    if e.action_kind == e.ADDED and e.old_name is not None:
                        mv_or_cp[e.old_name] = e
                
                entries = []
                for e in self.current['entries']:
                    if e.action_kind==e.DELETED and mv_or_cp.has_key(e.name):
                        mv_or_cp[e.name].action_kind = e.RENAMED
                    elif e.action_kind=='R':
                        if mv_or_cp.has_key(e.name):
                            mv_or_cp[e.name].action_kind = e.RENAMED
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
                                      self.current['author'],
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


    handler = SvnXMLLogHandler()
    parseString(log.read(), handler)
    return handler.changesets


class SvnWorkingDir(UpdatableSourceWorkingDir, SyncronizableTargetWorkingDir):

    ## UpdatableSourceWorkingDir

    def getUpstreamChangesets(self, root, repository, module, sincerev=None):
        if sincerev:
            sincerev = int(sincerev)
        else:
            sincerev = 0
            
        svnlog = SvnLog(working_dir=root)
        log = svnlog(quiet='--verbose', output=True, xml=True,
                     startrev=sincerev+1, entry='.')
        
        if svnlog.exit_status:
            return []

        svninfo = SvnInfo(working_dir=root)
        info = svninfo(entry='.')

        if svninfo.exit_status:
            raise GetUpstreamChangesetsFailure('svn info on %r exited with status %d' % (root, svninfo.exit_status))
        
        return self.__parseSvnLog(log, info['URL'], repository, module)

    def __parseSvnLog(self, log, url, repository, module):
        """Return an object representation of the ``svn log`` thru HEAD."""

        return changesets_from_svnlog(log, url, repository, module)
    
    def _applyChangeset(self, root, changeset, logger=None):
        svnup = SvnUpdate(working_dir=root)
        out = svnup(output=True, entry='.', revision=changeset.revision)

        if svnup.exit_status:
            raise ChangesetApplicationFailure(
                "'svn update' returned status %s" % svnup.exit_status)
            
        if logger: logger.info("%s updated to %s" % (
            ','.join([e.name for e in changeset.entries]),
            changeset.revision))
        
        result = []
        for line in out:
            if len(line)>2 and line[0] == 'C' and line[1] == ' ':
                logger.warn("Conflict after 'svn update': '%s'" % line)
                result.append(line[2:-1])
            
        return result
        
    def _checkoutUpstreamRevision(self, basedir, repository, module, revision,
                                  subdir=None, logger=None, **kwargs):
        """
        Concretely do the checkout of the upstream revision.
        """
        
        from os.path import join, exists
        
        wdir = join(basedir, subdir)

        if not exists(join(wdir, '.svn')):
            if logger: logger.info("checking out a working copy")
            svnco = SvnCheckout(working_dir=basedir)
            svnco(output=True, repository=repository, module=module,
                  wc=shrepr(subdir), revision=revision)
            if svnco.exit_status:
                raise TargetInitializationFailure(
                    "'svn checkout' returned status %s" % svnco.exit_status)
        else:
            if logger: logger.info("%s already exists, assuming it's a svn working dir" % wdir)

        svninfo = SvnInfo(working_dir=wdir)
        info = svninfo(entry='.')
        if svninfo.exit_status:
            raise GetUpstreamChangesetsFailure(
                'svn info on %r exited with status %d' %
                (wdir, svninfo.exit_status))        

        actual = info['Revision']
        
        if logger: logger.info("working copy up to svn revision %s",
                               actual)
        
        return actual 
    
    ## SyncronizableTargetWorkingDir

    def _addPathnames(self, root, names):
        """
        Add some new filesystem objects.
        """

        c = SystemCommand(working_dir=root,
                          command="svn add --quiet --no-auto-props "
                                  "--non-recursive %(names)s")
        c(names=' '.join([shrepr(n) for n in names]))

    def _commit(self,root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = SvnCommit(working_dir=root)
        
        logmessage = "%s\nOriginal author: %s\nDate: %s" % (remark, author,
                                                            date)
        if changelog:
            logmessage = logmessage + '\n\n' + changelog
            
        if entries:
            entries = ' '.join([shrepr(e) for e in entries])
        else:
            entries = '.'
            
        c(logmessage=logmessage, entries=entries)
        
    def _removePathnames(self, root, names):
        """
        Remove some filesystem objects.
        """

        c = SvnRemove(working_dir=root)
        c(entry=' '.join([shrepr(n) for n in names]))

    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        c = SvnMv(working_dir=root)
        c(old=shrepr(oldname), new=repr(newname))

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Add the given directory to an already existing svn working tree.
        """

        from os.path import exists, join

        if not exists(join(root, '.svn')):
            raise TargetInitializationFailure("'%s' needs to be an SVN working copy already under SVN" % root)

        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            repository, module,
                                                            subdir)
