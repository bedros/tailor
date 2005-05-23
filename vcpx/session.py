#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Interactive session
# :Creato:   ven 13 mag 2005 02:00:57 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 

"""
Tailor interactive session.

This module implements an alternative approach at driving the various
steps tipically performed by tailor, using an interaction with the user
instead of pushing options madness on him.
"""

__docformat__ = 'reStructuredText'

from cmd import Cmd
from os import chdir, getcwd       


INTRO = """\
Welcome to the Tailor interactive session: you can issue several commands
with the usual `readline` facilities. With "help" you'll get a list of
available commands.
"""

def yesno(arg):
    "Return True for '1', 'true' or 'yes', False otherwise."

    try:
        return bool(int(arg))
    except ValueError:
        return arg.lower() in ('true', 'yes')
    
class Session(Cmd):
    """Tailor interactive session."""
    
    prompt = "tailor $ "
    
    def __init__(self, options, args):
        """
        Initialize a new interactive session.

        Set the default values, and override them with option settings,
        then slurp in each command line argument that should contain
        a list of commands to be executed.
        """
        
        Cmd.__init__(self)
        self.options = options        
        self.args = args
        
        self.source_repository = options.repository
        self.source_kind = options.source_kind
        self.source_module = options.module
        self.target_repository = None
        self.target_kind = options.target_kind
        self.target_module = None
        self.current_directory = getcwd()
        self.sub_directory = None
        
        self.state_file = 'tailor.state'
        
        self.changesets = None
        self.logfile = None
        self.logger = None
        
        self.__processArgs()

    def __processArgs(self):
        """
        Process optional command line arguments.

        Each argument is assumed to contain a list of tailor commands
        to execute in order.
        """

        for arg in self.args:
            self.cmdqueue.extend(file(arg).readlines())

    def __log(self, what):
        if self.logger:
            self.logger.info(what)
            
        if self.options.verbose:
            self.stdout.write(what)

    def __err(self, what):
        if self.logger:
            self.logger.error(what)
            
        self.stdout.write('Error: ')
        self.stdout.write(what)
        

    ## Interactive commands

    def emptyline(self):
        """Override the default impl of reexecuting last command."""
        pass
        
    def do_exit(self, arg):
        """
        Usage: exit

        Terminate the interactive session. This is the same thing
        happening upon EOF (Ctrl-D).
        """

        self.__log('Exiting...\n')
        return True

    do_EOF = do_exit

    def do_save(self, arg):
        """
        Usage: save filename

        Save the commands history on the specified file.
        """

        import readline

        if not arg:
            return
            
        readline.write_history_file(arg)
        self.__log('History saved in: %s\n' % arg)
        
    def do_cd(self, arg):
        """
        Usage: cd [dirname]

        Print or set current active directory.
        """

        if arg and self.current_directory <> arg:
            try:
                chdir(arg)
                self.current_directory = getcwd()
            except:
                self.__log('Cannot change current directory to %s\n' %
                           arg)
        self.__log('Current directory: %s\n' % self.current_directory)

    do_current_directory = do_cd

    def do_sub_directory(self, arg):
        """
        Usage: sub_directory dirname
        
        Print or set the subdirectory that actually contains the
        working copy. When not explicitly set, this is desumed from
        the last component of the upstream module name or repository.
        """
        
        if arg and self.sub_directory <> arg:
            self.sub_directory = arg

        self.__log('Sub directory: %s\n' % self.sub_directory)

    def do_logfile(self, arg):
        """
        Usage: logfile [filename]
        
        Print or set the logfile of operations. By default there's no log.
        """

        import logging
        
        if arg:
            self.logfile = arg
            self.logger = logging.getLogger('tailor')
            hdlr = logging.FileHandler(self.logfile)
            formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
            hdlr.setFormatter(formatter)
            self.logger.addHandler(hdlr) 
            self.logger.setLevel(logging.INFO)
            
        self.__log('Logging to: %s\n' % self.logfile)

    def do_print_executed_commands(self, arg):
        """
        Usage: print_executed_commands [0|1]

        Print or set the verbosity on external commands execution.
        """

        from shwrap import SystemCommand
        
        if arg:
            SystemCommand.VERBOSE = yesno(arg)

        self.__log('Print executed commands: %s\n' % SystemCommand.VERBOSE)

    def do_patch_name_format(self, arg):
        """
        Usage: patch_name_format [format]

        Print or set the patch name format, ie the prototype that will
        be used to compute the patch name.

        The prototype may contain %(keyword)s such as 'module',
        'author', 'date', 'revision', 'firstlogline', 'remaininglog'
        for normal updates, otherwise 'module', 'authors',
        'nchangesets', 'mindate' and 'maxdate'.
        """

        from target import SyncronizableTargetWorkingDir

        if arg:
            SyncronizableTargetWorkingDir.PATCH_NAME_FORMAT = arg

        self.__log('Patch name format: %s\n' %
                   SyncronizableTargetWorkingDir.PATCH_NAME_FORMAT)
        
    def do_remove_first_log_line(self, arg):
        """
        Usage: remove_first_log_line [0|1]
        
        Print or set if tailor should drop the first line of the
        upstream changelog.

        This is intended to go in pair with patch_name_format, when
        using it's 'firstlogline' variable to build the name of the
        patch.
        """

        from target import SyncronizableTargetWorkingDir

        if arg:
            SyncronizableTargetWorkingDir.REMOVE_FIRST_LOG_LINE = yesno(arg)

        self.__log('Remove first log line: %s\n' %
                   SyncronizableTargetWorkingDir.REMOVE_FIRST_LOG_LINE)

    def do_refill_changelogs(self, arg):
        """
        Usage: refill_changelogs [0|1]

        Print or set if tailor should refill the upstream changelogs,
        as it does by default.
        """

        from changes import Changeset
        
        if arg:
            Changeset.REFILL_MESSAGE = yesno(arg)

        self.__log('Refill changelogs: %s\n' % Changeset.REFILL_MESSAGE)
        
    def do_source_kind(self, arg):
        """
        Usage: source_kind [svn|darcs|cvs]

        Print or set the source repository kind.
        """

        if arg and self.source_kind <> arg:
            self.source_kind = arg

        self.__log('Current source kind: %s\n' % self.source_kind)
        
    def do_target_kind(self, arg):
        """
        Usage: target_kind [svn|darcs|cvs|monotone|cdv|bzr]

        Print or set the target repository kind.
        """

        if arg and self.target_kind <> arg:
            self.target_kind = arg

        self.__log('Current target kind: %s\n' % self.target_kind)

    def do_source_repository(self, arg):
        """
        Usage: source_repository [repos]

        Print or set the source repository.
        """

        from os.path import sep
        
        if arg and self.source_repository <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.source_repository = arg

        self.__log('Current source repository: %s\n' % self.source_repository)

    def do_target_repository(self, arg):
        """
        Usage: target_repository [repos]

        Print or set the target repository. This is currently unused.
        """

        from os.path import sep
        
        if arg and self.target_repository <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.target_repository = arg

        self.__log('Current target repository: %s\n' % self.target_repository)

    def do_source_module(self, arg):
        """
        Usage: source_module [module]
        
        Print or set the source module.
        """

        from os.path import sep
        
        if arg and self.source_module <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.source_module = arg

        self.__log('Current target kind: %s\n' % self.source_module)

    def do_target_module(self, arg):
        """
        Usage: target_module [module]

        Print or set the target module. This is currently not used.
        """

        from os.path import sep
        
        if arg and self.target_module <> arg:
            if arg.endswith(sep):
                arg = arg[:-1]
            self.target_module = arg

        self.__log('Current target kind: %s\n' % self.target_module)

    def readSourceRevision(self):
        """Read the source revision from the state file."""

        try:
            sf = open(self.state_file)
            revision = sf.read()
            sf.close()
        except IOError:
            revision = None

        return revision
            
    def saveSourceRevision(self, revision):
        """Write current source revision in the state file."""

        sf = open(self.state_file, 'w')
        sf.write(revision)
        sf.close()
        
    def do_state_file(self, arg):
        """
        Usage: state_file [filename]
        
        Print or set the current state file, where tailor stores the
        source revision that has been applied last.
        
        The argument must be a file name, possibly with the usual
        "~user/file" convention.        
        """

        from os.path import isabs, abspath, expanduser

        if arg:
            arg = expanduser(arg)
            if not isabs(arg):
                arg = abspath(arg)
        
        if arg and self.state_file <> arg:
            self.state_file = arg
                
        self.__log('Current state file: %s\n' % self.state_file)

    def do_bootstrap(self, arg):
        """
        Usage: bootstrap [revision]
        
        Checkout the initial upstream revision, by default HEAD (or
        specified by argument), then import the subtree into the
        target repository.
        """
        
        from os.path import join, split, sep
        from dualwd import DualWorkingDir

        if self.sub_directory:
            subdir = self.sub_directory
        else:
            subdir = split(self.source_module or self.source_repository)[1] or ''
            self.do_sub_directory(subdir)

        revision = arg or self.options.revision or 'HEAD'
        
        dwd = DualWorkingDir(self.source_kind, self.target_kind)
        self.__log("Getting %s revision '%s' of '%s' from '%s'\n" % (
            self.source_kind, revision,
            self.source_module, self.source_repository))

        try:
            actual = dwd.checkoutUpstreamRevision(self.current_directory,
                                                  self.source_repository,
                                                  self.source_module,
                                                  revision,
                                                  subdir=subdir,
                                                  logger=self.logger)
            self.saveSourceRevision(actual)
        except Exception, exc:
            self.__err('Checkout failed: %s, %s' % (exc.__doc__, exc))
            if self.logger:
                self.logger.exception('Checkout failed')

        try:
            dwd.initializeNewWorkingDir(self.current_directory,
                                        self.target_repository,
                                        self.target_module,
                                        self.sub_directory,
                                        actual)
        except:
            self.__err('Working copy initialization failed: %s, %s' % (exc.__doc__, exc))
            if self.logger:
                self.logger.exception('Working copy initialization failed')

    def willApply(self, root, changeset):
        """
        Print the changeset being applied.
        """

        self.__log("Changeset %s:\n%s\n" % (changeset.revision,
                                            changeset.log))
        return True

    def shouldApply(self, root, changeset):
        """
        Ask weather a changeset should be applied.
        """

        self.stdout.write("Changeset %s:\n%s\n" % (changeset.revision,
                                                   changeset.log))
        ans = raw_input("Apply [Y/n]? ")
        
        return ans == '' or ans[0].lower() == 'y'

    def applied(self, root, changeset):
        """
        Save current status.
        """

        self.saveSourceRevision(changeset.revision)

    def do_update(self, arg):
        """
        Usage: update [arg]

        Fetch information on upstream changes and replay them with the
        target system.

        Argument may be either an integer value or the string 'ask'. The
        number specify the maximum number of changesets the will be
        applied. With 'ask' tailor will propose a "y/n" question for each
        changeset before applying it.
        """

        source_revision = self.readSourceRevision()
        if self.source_kind and \
           self.source_repository and \
           self.source_module and \
           source_revision:

            dwd = DualWorkingDir(self.source_kind, self.target_kind)
            self.changesets = dwd.getUpstreamChangesets(self.current_directory,
                                                        self.source_repository,
                                                        self.source_module,
                                                        source_revision)
            nchanges = len(changesets)
            if nchanges:
                self.__log('Collected %d upstream changesets\n' % nchanges)

                if arg:
                    appliable = self.willApply
                    try:
                        howmany = min(int(arg), nchanges)
                        changesets = changesets[:howmany]
                        self.__log('Applying first %d of them\n' % howmany)
                    except ValueError:
                        if arg.lower() == 'ask':
                            appliable = self.shouldApply

                try:
                    last, conflicts = dwd.applyUpstreamChangesets(
                        proj, self.module, changesets, applyable=applyable,
                        applied=self.applied, logger=self.logger,
                        delayed_commit=single_commit)
                except:
                    if self.logger:
                        self.logger.exception('Upstream change application '
                                              'failed')
                    self.__err('Stopping after upstream change application '
                               'failure.')
                    return

                if last:
                    self.__log("Update completed, now at revision '%s'" %
                               self.readSourceRevision())
            else:
                self.__log("Update completed with no upstream changes")
        else:
            self.__err("needs 'source_kind', 'source_repository' and "
                       "'source_module' to proceed.\n")

        
def interactive(options, args):
    session = Session(options, args)
    session.cmdloop(options.verbose and INTRO or "")
