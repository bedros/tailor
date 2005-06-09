#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Darcs details
# :Creato:   ven 18 giu 2004 14:45:28 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 

"""
This module contains supporting classes for the ``darcs`` versioning system.
"""

__docformat__ = 'reStructuredText'

from shwrap import SystemCommand, shrepr
from source import UpdatableSourceWorkingDir, ChangesetApplicationFailure, \
     GetUpstreamChangesetsFailure
from target import SyncronizableTargetWorkingDir, TargetInitializationFailure
from xml.sax import SAXException

MOTD = """\
This is the Darcs equivalent of
%s/%s
"""

class DarcsRecord(SystemCommand):
    COMMAND = "darcs record --all --pipe %(entries)s"

    def __call__(self, output=None, dry_run=False, **kwargs):
        date = kwargs.get('date').strftime('%Y/%m/%d %H:%M:%S')
        author = kwargs.get('author')
        patchname = kwargs.get('patchname')
        logmessage = kwargs.get('logmessage')
        if not logmessage:
            logmessage = ''

        input = "%s UTC\n%s\n%s\n%s\n" % (date, author, patchname, logmessage)
        
        return SystemCommand.__call__(self, output=output, input=input,
                                      dry_run=dry_run, 
                                      **kwargs)


def changesets_from_darcschanges(changes):
    """
    Parse XML output of ``darcs changes``.

    Return a list of ``Changeset`` instances.
    """
    
    from xml.sax import parseString
    from xml.sax.handler import ContentHandler
    from changes import ChangesetEntry, Changeset
    from datetime import datetime

    class DarcsXMLChangesHandler(ContentHandler):
        def __init__(self):
            self.changesets = []
            self.current = None
            self.current_field = []

        def startElement(self, name, attributes):
            if name == 'patch':
                self.current = {}
                self.current['author'] = attributes['author']
                date = attributes['date']
                # 20040619130027
                y = int(date[:4])
                m = int(date[4:6])
                d = int(date[6:8])
                hh = int(date[8:10])
                mm = int(date[10:12])
                ss = int(date[12:14])
                timestamp = datetime(y, m, d, hh, mm, ss)
                self.current['date'] = timestamp
                self.current['comment'] = ''
                self.current['entries'] = []
            elif name in ['name', 'comment',
                          'add_file', 'add_directory',
                          'modify_file', 'remove_file']:
                self.current_field = []
            elif name == 'move':
                self.old_name = attributes['from']
                self.new_name = attributes['to']

        def endElement(self, name):
            if name == 'patch':
                # Sort the paths to make tests easier
                self.current['entries'].sort(lambda x,y: cmp(x.name, y.name))
                self.changesets.append(Changeset(self.current['name'],
                                                 self.current['date'],
                                                 self.current['author'],
                                                 self.current['comment'],
                                                 self.current['entries']))
                self.current = None
            elif name in ['name', 'comment']:
                self.current[name] = ''.join(self.current_field)
            elif name == 'move':
                entry = ChangesetEntry(self.new_name)
                entry.action_kind = entry.RENAMED
                entry.old_name = self.old_name
                self.current['entries'].append(entry)
            elif name in ['add_file', 'add_directory',
                          'modify_file', 'remove_file']:
                entry = ChangesetEntry(''.join(self.current_field).strip())
                entry.action_kind = { 'add_file': entry.ADDED,
                                      'add_directory': entry.ADDED,
                                      'modify_file': entry.UPDATED,
                                      'remove_file': entry.DELETED,
                                      'rename_file': entry.RENAMED
                                    }[name]

                self.current['entries'].append(entry)

        def characters(self, data):
            self.current_field.append(data)

    handler = DarcsXMLChangesHandler()
    try:
        parseString(changes.getvalue(), handler)
    except SAXException, le:
        print "parseString(%s, %s) yielded the following error..." % (changes.getValue(), handler,)
        raise le

    changesets = handler.changesets
    
    # sort changeset by date
    changesets.sort(lambda x, y: cmp(x.date, y.date))

    return changesets

    
class DarcsWorkingDir(UpdatableSourceWorkingDir,SyncronizableTargetWorkingDir):
    """
    A working directory under ``darcs``.
    """

    ## UpdatableSourceWorkingDir
    
    def getUpstreamChangesets(self, root, repository, module, sincerev=None):
        """
        Do the actual work of fetching the upstream changeset.
        """

        from datetime import datetime
        from time import strptime
        from changes import Changeset
        
        c = SystemCommand(working_dir=root,
                          command="TZ=UTC darcs pull --dry-run %(repository)s")
        output = c(output=True, repository=shrepr(repository))
        if c.exit_status:
            raise GetUpstreamChangesetsFailure("'darcs pull' returned status %d saying \"%s\"" % (c.exit_status, output.getvalue().strip()))
        
        l = output.readline()
        while l and not (l.startswith('Would pull the following changes:') or
                         l == 'No remote changes to pull in!\n'):
            l = output.readline()

        changesets = []

        if l <> 'No remote changes to pull in!\n':
            ## Sat Jul 17 01:22:08 CEST 2004  lele@nautilus
            ##   * Refix _getUpstreamChangesets for darcs

            l = output.readline()
            while not l.startswith('Making no changes:  this is a dry run.'):
                # Assume it's a line like
                #    Sun Jan  2 00:24:04 UTC 2005  lele@nautilus.homeip.net
                # we used to split on the double space before the email,
                # but in this case this is wrong. Waiting for xml output,
                # is it really sane asserting date's length to 28 chars?
                date = l[:28]
                author = l[30:-1]
                y,m,d,hh,mm,ss,d1,d2,d3 = strptime(date, "%a %b %d %H:%M:%S %Z %Y")
                date = datetime(y,m,d,hh,mm,ss)
                l = output.readline()
                assert (l.startswith('  * ') or
                        l.startswith('  UNDO:') or
                        l.startswith('  tagged'))

                if l.startswith('  *'):
                    name = l[4:-1]
                else:
                    name = l[2:-1]

                changelog = []
                l = output.readline()
                while l.startswith(' '):
                    changelog.append(l.strip())
                    l = output.readline()

                changesets.append(Changeset(name, date, author, '\n'.join(changelog)))

                while not l.strip():
                    l = output.readline()

        return changesets
    
    def _applyChangeset(self, root, changeset, logger=None):
        """
        Do the actual work of applying the changeset to the working copy.
        """

        patchname=shrepr(changeset.revision)
        
        c = SystemCommand(working_dir=root,
                          command="darcs pull --all --patches=%(patch)s")
        output = c(output=True, patch=patchname)
        if c.exit_status:
            raise ChangesetApplicationFailure("'darcs pull' returned status %d saying \"%s\"" % (c.exit_status, output.getvalue().strip()))

        c = SystemCommand(working_dir=root,
                          command="darcs changes --patches=%(patch)s"
                                  " --xml-output --summ")
        last = changesets_from_darcschanges(c(output=True, patch=patchname))
        if last:
            changeset.entries.extend(last[0].entries)

    def _checkoutUpstreamRevision(self, basedir, repository, module, revision,
                                  subdir=None, logger=None, **kwargs):
        """
        Concretely do the checkout of the upstream revision.
        """

        from os.path import join, exists
        from os import mkdir

        if subdir == '.':
            # This is currently *very* slow, compared to the darcs get
            # below!
            wdir = basedir
            if not exists(join(wdir, '_darcs')):
                if not exists(wdir):
                    mkdir(wdir)

                c = SystemCommand(working_dir=wdir, command="darcs initialize")
                c(output=True)

                if c.exit_status:
                    raise TargetInitializationFailure(
                        "'darcs initialize' returned status %s"%c.exit_status)

                dpull = SystemCommand(working_dir=wdir,
                                     command="darcs pull --all --verbose"
                                             " %(tag)s %(repository)s"
                                             " 2>&1")

                output = dpull(output=True, repository=shrepr(repository),
                               tag=(revision<>'HEAD' and
                                    '--tag=%s' % shrepr(revision)
                                    or ''))
                if dpull.exit_status:
                    raise TargetInitializationFailure(
                        "'darcs pull' returned status %d saying \"%s\"" %
                        (dpull.exit_status, output.getvalue().strip()))
        else:
            # Use much faster 'darcs get'
            
            wdir = join(basedir, subdir)           
            dget = SystemCommand(working_dir=basedir,
                                 command="darcs get --partial --verbose"
                                         " %(tag)s '%(repository)s'"
                                         " %(subdir)s")

            output = dget(output=True, repository=repository,
                          tag=(revision<>'HEAD' and
                               '--tag=%s' % shrepr(revision) or ''),
                          subdir=subdir)
            
            if dget.exit_status:
                raise TargetInitializationFailure(
                    "'darcs get' returned status %d saying \"%s\"" %
                    (dget.exit_status, output.getvalue().strip()))

        c = SystemCommand(working_dir=wdir,
                          command="darcs changes --last=1 --xml-output 2>&1")
        output = c(output=True)
        if c.exit_status:
            raise ChangesetApplicationFailure("'darcs changes' returned status %d saying \"%s\"" % (c.exit_status, output.getvalue().strip()))
        
        last = changesets_from_darcschanges(output)
        
        return last[0].revision

    
    ## SyncronizableTargetWorkingDir
   
    def _addPathnames(self, root, names):
        """
        Add some new filesystems objects.
        """

        c = SystemCommand(working_dir=root,
                          command="darcs add --case-ok --not-recursive"
                                  " --quiet %(names)s")
        c(names=' '.join([shrepr(n) for n in names]))
        
    def _addSubtree(self, root, subdir):
        """
        Use the --recursive variant of ``darcs add`` to add a subtree.
        """
        
        c = SystemCommand(working_dir=root,
                          command="darcs add --case-ok --recursive"
                          " --quiet %(entry)s")
        c(entry=shrepr(subdir))
        
    def _commit(self, root, date, author, remark, changelog=None, entries=None):
        """
        Commit the changeset.
        """

        c = DarcsRecord(working_dir=root)

        if entries:
            entries = ' '.join([shrepr(e) for e in entries])
        else:
            entries = '.'
            
        c(output=True, date=date, patchname=remark,
          logmessage=changelog, author=author, entries=entries)
        if c.exit_status:
            raise ChangesetApplicationFailure("'darcs record' returned status %d" % c.exit_status)
        
    def _removePathnames(self, root, names):
        """
        Remove some filesystem object.
        """

        # Since the source VCS already deleted the entry, and given that
        # darcs will do the right thing with it, do nothing here, instead
        # of 
        #         c = SystemCommand(working_dir=root,
        #                           command="darcs remove %(entry)s")
        #         c(entry=' '.join([e.name for e in entries]))
        # that raises status 512 on darcs not finding the entry.

        pass
    
    def _renamePathname(self, root, oldname, newname):
        """
        Rename a filesystem object.
        """

        from os.path import join, exists
        from os import rename
        
        # Check to see if the oldentry is still there. If it does,
        # that probably means one thing: it's been moved and then
        # replaced, see svn 'R' event. In this case, rename the
        # existing old entry to something else to trick "darcs mv"
        # (that will assume the move was already done manually) and
        # finally restore its name.

        renamed = exists(join(root, oldname))
        if renamed:
            rename(oldname, oldname + '-TAILOR-HACKED-TEMP-NAME')

        try:
            c = SystemCommand(working_dir=root,
                              command="darcs mv %(old)s %(new)s")
            c(old=shrepr(oldname), new=shrepr(newname))
        finally:
            if renamed:
                rename(oldname + '-TAILOR-HACKED-TEMP-NAME', oldname)

    def _initializeWorkingDir(self, root, repository, module, subdir):
        """
        Execute ``darcs initialize`` and tweak the default settings of
        the repository, then add the whole subtree.
        """

        from os.path import join
        
        c = SystemCommand(working_dir=root, command="darcs initialize")
        c(output=True)

        if c.exit_status:
            raise TargetInitializationFailure(
                "'darcs initialize' returned status %s" % c.exit_status)

        motd = open(join(root, '_darcs/prefs/motd'), 'w')
        motd.write(MOTD % (repository, module))
        motd.close()

        boring = open(join(root, '_darcs/prefs/boring'), 'a')
        boring.write('^tailor.log$\n^tailor.info$\n^.cdv\n^MT\n')
        boring.close()
        
        SyncronizableTargetWorkingDir._initializeWorkingDir(self, root,
                                                            repository, module,
                                                            subdir)
