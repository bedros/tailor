#  -*- Python -*- -*- coding: iso-8859-1 -*-
# :Progetto: Bice -- Sync CVS->SVN
# :Sorgente: $HeadURL: http://svn.bice.dyndns.org/progetti/wip/tools/cvsync/shwrap.py $
# :Creato:   sab 10 apr 2004 16:43:48 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Modifica: $LastChangedDate: 2004-05-21 14:33:02 +0200 (ven, 21 mag 2004) $
# :Fatta da: $LastChangedBy: lele $
# 

__docformat__ = 'reStructuredText'

from StringIO import StringIO
from sys import stderr

class VerboseStringIO(StringIO):

    def write(self, data):        
        """Give a feedback to the user."""
        
        StringIO.write(self, data)
        stderr.write('.'*data.count('\n'))


class SystemCommand(object):
    """Wrap a single command to be executed by the shell."""

    COMMAND = None
    """The default command for this class.  Must be redefined by subclasses."""

    VERBOSE = True
    """Print the executed command on stderr, at each run."""
    
    def __init__(self, command=None, working_dir=None):
        """Initialize a SystemCommand instance, specifying the command
           to be executed and eventually the working directory."""
        
        self.command = command or self.COMMAND
        """The command to be executed."""
        
        self.working_dir = working_dir
        """The working directory, go there before execution."""
        
        self.exit_status = None
        """Once the command has been executed, this is its exit status."""
        
    def __call__(self, output=None, dry_run=False, **kwargs):
        """Execute the command."""
        
        from os import system, popen, chdir
        from shutil import copyfileobj
        
        wdir = self.working_dir or kwargs.get('working_dir')
        if wdir:
            if self.VERBOSE:
                stderr.write("cd %s\n" % wdir)
            chdir(wdir)

        command = self.command % kwargs
        if self.VERBOSE:
            stderr.write("%s " % command)

        if dry_run:
            if self.VERBOSE:
                stderr.write(" [dry run]\n")
            return
        
        if output:
            if output is True:
                if self.VERBOSE:
                    output = VerboseStringIO()
                else:
                    output = StringIO()
                
            out = popen(command)
            copyfileobj(out, output, length=128)
            output.seek(0)

            self.exit_status = out.close()
        else:
            self.exit_status = system(command)            
                    
        if self.VERBOSE:
            if not self.exit_status:
                stderr.write(" [Ok]\n")
            else:
                stderr.write(" [Error %s]\n" % self.exit_status)
                
        return output
