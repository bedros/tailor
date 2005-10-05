# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- svn specific tests
# :Creato:   gio 11 nov 2004 19:09:06 CET
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
#

from unittest import TestCase
from datetime import datetime
from StringIO import StringIO
from vcpx.svn import changesets_from_svnlog

class SvnLogParser(TestCase):
    """Ensure the svn log parser does its job"""

    SIMPLE_RENAME_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="2">
<author>lele</author>
<date>2004-11-12T15:05:37.134366Z</date>
<paths>
<path
   action="A">/trunk/dir</path>
<path
   action="A">/trunk/dir/a.txt</path>
</paths>
<msg>create tree</msg>
</logentry>
<logentry
   revision="3">
<author>lele</author>
<date>2004-11-12T15:06:04.193650Z</date>
<paths>
<path
   action="D">/trunk/dir</path>
<path
   copyfrom-path="/trunk/dir"
   copyfrom-rev="1"
   action="A">/trunk/new</path>
</paths>
<msg>rename dir</msg>
</logentry>
</log>
"""

    def testRenameBehaviour(self):
        """Verify svn log parser behaves correctly on renames"""

        log = StringIO(self.SIMPLE_RENAME_TEST)
        csets = changesets_from_svnlog(log,
                                       'file:///tmp/t/repo',
                                       '/trunk')
        self.assertEqual(len(csets), 2)

        cset = csets[0]
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2004,11,12,15,05,37,134366))
        self.assertEqual(cset.log, 'create tree')
        self.assertEqual(len(cset.entries), 2)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'dir')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'dir/a.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)

        cset = csets[1]
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2004,11,12,15,06,04,193650))
        self.assertEqual(cset.log, 'rename dir')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'new')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'dir')

    RENAME_OUT_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="894">
<author>anthony</author>
<date>2004-11-09T06:54:20.709243Z</date>
<paths>
<path
   action="D">/trunk/shtoom/tmp</path>
<path
   copyfrom-path="/trunk/shtoom/tmp"
   copyfrom-rev="893"
   action="A">/sandbox</path>
</paths>
<msg>Moving to a /sandbox
</msg>
</logentry>
</log>
"""

    def testRenameOutBehaviour(self):
        """Verify svn log parser behaves correctly on renames outside tracked tree"""

        log = StringIO(self.RENAME_OUT_TEST)
        csets = changesets_from_svnlog(log,
                                       'http://server/svn/Shtoom',
                                       '/trunk')
        self.assertEqual(len(csets), 1)

        cset = csets[0]
        self.assertEqual(cset.author, 'anthony')
        self.assertEqual(cset.date, datetime(2004,11,9,6,54,20,709243))
        self.assertEqual(cset.log, 'Moving to a /sandbox')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'shtoom/tmp')
        self.assertEqual(entry.action_kind, entry.DELETED)

    COPY_AND_RENAME_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="1">
<author>lele</author>
<date>2005-01-08T17:36:39.131126Z</date>
<paths>
<path
   action="A">/test/file1.txt</path>
</paths>
<msg>First commit</msg>
</logentry>
<logentry
   revision="2">
<author>lele</author>
<date>2005-01-08T17:36:55.174757Z</date>
<paths>
<path
   copyfrom-path="/test/file1.txt"
   copyfrom-rev="1"
   action="A">/test/file2.txt</path>
</paths>
<msg>Copy</msg>
</logentry>
<logentry
   revision="3">
<author>lele</author>
<date>2005-01-08T17:42:41.347315Z</date>
<paths>
<path
   action="D">/test/file1.txt</path>
</paths>
<msg>Remove</msg>
</logentry>
<logentry
   revision="4">
<author>lele</author>
<date>2005-01-08T17:43:09.909127Z</date>
<paths>
<path
   copyfrom-path="/test/file2.txt"
   copyfrom-rev="2"
   action="A">/test/file1.txt</path>
<path
   action="D">/test/file2.txt</path>
</paths>
<msg>Move</msg>
</logentry>
</log>
"""

    def testCopyAndRename(self):
        """Verify svn log parser behaves correctly on copies"""

        log = StringIO(self.COPY_AND_RENAME_TEST)
        csets = changesets_from_svnlog(log,
                                       'file:///tmp/rep',
                                       '/test')
        self.assertEqual(len(csets), 4)

        cset = csets[1]
        self.assertEqual(cset.author, 'lele')
        self.assertEqual(cset.date, datetime(2005,1,8, 17,36,55,174757))
        self.assertEqual(cset.log, 'Copy')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file2.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)
        self.assertEqual(entry.old_name, 'file1.txt')

        cset = csets[2]
        self.assertEqual(cset.date, datetime(2005,1,8, 17,42,41,347315))
        self.assertEqual(cset.log, 'Remove')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file1.txt')
        self.assertEqual(entry.action_kind, entry.DELETED)

        cset = csets[3]
        self.assertEqual(cset.date, datetime(2005,1,8, 17,43,9,909127))
        self.assertEqual(cset.log, 'Move')
        self.assertEqual(len(cset.entries), 1)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'file1.txt')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'file2.txt')

    SVN_R_EVENT_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="1378">
<author>cmlenz</author>
<date>2005-03-21T08:06:13.381116Z</date>
<paths>
<path
   action="M">/trunk/trac/db.py</path>
</paths>
<msg>Fix to the database connection wrapper in {{{trac/db.py}}}, which would cause infinite recursion when initialization failed. Closes #1327. Thanks to Mark Rowe for the patch.</msg>
</logentry>
<logentry
   revision="1379">
<author>cmlenz</author>
<date>2005-03-21T08:34:02.522947Z</date>
<paths>
<path
   copyfrom-path="/trunk/scripts/trac-admin"
   copyfrom-rev="1377"
   action="A">/trunk/trac/scripts/admin.py</path>
<path
   action="A">/trunk/trac/scripts</path>
<path
   action="M">/trunk/trac/tests/tracadmin.py</path>
<path
   action="R">/trunk/scripts/trac-admin</path>
<path
   action="A">/trunk/trac/scripts/__init__.py</path>
<path
   action="M">/trunk/trac/tests/environment.py</path>
<path
   action="M">/trunk/setup.py</path>
</paths>
<msg>Applied Mark Rowe's patch for refactoring trad-admin into a real module so that the unit tests don't need to invoke it through the shell. Closes #1328. Many thanks.</msg>
</logentry>
</log>
"""

    def testREvent(self):
        """Verify how tailor handle svn "R" event"""

        log = StringIO(self.SVN_R_EVENT_TEST)
        csets = changesets_from_svnlog(log,
                                       'file:///tmp/rep',
                                       '/trunk')
        self.assertEqual(len(csets), 2)

        cset = csets[1]
        self.assertEqual(cset.author, 'cmlenz')
        self.assertEqual(cset.date, datetime(2005,3,21, 8,34,02,522947))
        self.assertEqual(len(cset.entries), 7)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'scripts/trac-admin')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'setup.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'trac/scripts')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[3]
        self.assertEqual(entry.name, 'trac/scripts/__init__.py')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[4]
        self.assertEqual(entry.name, 'trac/scripts/admin.py')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'scripts/trac-admin')

        entry = cset.entries[5]
        self.assertEqual(entry.name, 'trac/tests/environment.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

    SVN_REPOS_ROOT_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="2">
<author>lele</author>
<date>2005-04-14T20:32:24.686518Z</date>
<paths>
<path
   action="A">/trunk/a.txt</path>
<path
   action="A">/trunk/b.txt</path>
</paths>
<msg>Some files in trunk</msg>
</logentry>
<logentry
   revision="3">
<author>lele</author>
<date>2005-04-14T20:32:55.602712Z</date>
<paths>
<path
   copyfrom-path="/trunk"
   copyfrom-rev="1"
   action="A">/branches/branch-a</path>
<path
   copyfrom-path="/trunk/a.txt"
   copyfrom-rev="2"
   action="A">/branches/branch-a/a.txt</path>
<path
   copyfrom-path="/trunk/b.txt"
   copyfrom-rev="2"
   action="A">/branches/branch-a/b.txt</path>
</paths>
<msg>Branched A</msg>
</logentry>
<logentry
   revision="4">
<author>lele</author>
<date>2005-04-14T20:34:25.374254Z</date>
<paths>
<path
   action="M">/branches/branch-a/a.txt</path>
<path
   action="M">/branches/branch-a/b.txt</path>
</paths>
<msg>Capitalization</msg>
</logentry>
<logentry
   revision="5">
<author>lele</author>
<date>2005-04-14T20:35:44.753550Z</date>
<paths>
<path
   action="M">/trunk/a.txt</path>
<path
   action="M">/trunk/b.txt</path>
</paths>
<msg>Merged back</msg>
</logentry>
</log>
"""

    def testTrackingRoot(self):
        """Verify we are able to track the root of the repository"""

        log = StringIO(self.SVN_REPOS_ROOT_TEST)
        csets = changesets_from_svnlog(log,
                                       'svn+ssh://caia/tmp/svn',
                                       '/')
        self.assertEqual(len(csets), 4)

        cset = csets[1]
        self.assertEqual(len(cset.entries), 3)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'branches/branch-a')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'branches/branch-a/a.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'branches/branch-a/b.txt')
        self.assertEqual(entry.action_kind, entry.ADDED)

    PYDIST_STRANGE_CASE = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="7969">
<author>hpk</author>
<date>2004-12-22T10:30:39.458701Z</date>
<paths>
<path
   copyfrom-path="/py/dist/example/test"
   copyfrom-rev="7968"
   action="R">/py/dist/py/documentation/example/test</path>
<path
   action="D">/py/dist/example</path>
<path
   copyfrom-path="/py/dist/example"
   copyfrom-rev="7965"
   action="A">/py/dist/py/documentation/example</path>
<path
   action="M">/py/dist/py/documentation/test.txt</path>
</paths>
<msg>moved example directory below the documentation directory lib

</msg>
</logentry>
</log>
"""
    def testPydistStrangeCase(self):
        """Verify we are able to groke with svn 'R' strangeness"""

        log = StringIO(self.PYDIST_STRANGE_CASE)
        csets = changesets_from_svnlog(log,
                                       'http://codespeak.net/svn',
                                       '/py/dist')

        self.assertEqual(len(csets), 1)

        cset = csets[0]
        self.assertEqual(len(cset.entries), 3)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'py/documentation/example')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'example')

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'py/documentation/example/test')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'py/documentation/test.txt')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        log = StringIO(self.PYDIST_STRANGE_CASE)
        csets = changesets_from_svnlog(log,
                                       'http://codespeak.net/svn',
                                       '/py/dist/py')

        self.assertEqual(len(csets), 1)

        cset = csets[0]
        self.assertEqual(len(cset.entries), 3)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'documentation/example')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'documentation/example/test')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'documentation/test.txt')
        self.assertEqual(entry.action_kind, entry.UPDATED)

    ENCODING_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="7564">
<author>fschulze</author>
<date>2005-07-20T17:47:53.425055Z</date>
<msg>Fix http://members.plone.org/collector/4034 — Collapsible fieldsets need a full width mode.</msg>
</logentry>
</log>
"""
    def testUnicode(self):
        """Verify svn parser returns unicode strings"""

        log = StringIO(self.ENCODING_TEST)
        csets = changesets_from_svnlog(log,
                                       'http://svn.plone.org/plone/CMFPlone',
                                       '/branches/2.1')

        self.assertEqual(len(csets), 1)

        log = csets[0].log
        self.assertEqual(type(log), type(u'€'))
        self.assertEqual(len(log), 91)
        self.assertRaises(UnicodeEncodeError, log.encode, 'iso-8859-1')
        self.assertEqual(len(log.encode('ascii', 'ignore')), 90)

    COPY_AND_REPLACE_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="1379">
<author>cmlenz</author>
<date>2005-03-21T08:34:02.522947Z</date>
<paths>
<path
   copyfrom-path="/trunk/scripts/trac-admin"
   copyfrom-rev="1377"
   action="A">/trunk/trac/scripts/admin.py</path>
<path
   action="A">/trunk/trac/scripts</path>
<path
   action="M">/trunk/trac/tests/tracadmin.py</path>
<path
   action="R">/trunk/scripts/trac-admin</path>
<path
   action="A">/trunk/trac/scripts/__init__.py</path>
<path
   action="M">/trunk/trac/tests/environment.py</path>
<path
   action="M">/trunk/setup.py</path>
</paths>
<msg>Applied Mark Rowe's patch for refactoring trad-admin into a real module so that the unit tests don't need to invoke it through the shell. Closes #1328. Many thanks.</msg>
</logentry>
</log>
"""

    def testCopyAndReplace(self):
        """Verify the svn parser handle copy+replace"""

        log = StringIO(self.COPY_AND_REPLACE_TEST)
        csets = changesets_from_svnlog(log,
                                       'http://svn.edgewall.com/repos/trac',
                                       '/trunk')

        self.assertEqual(len(csets), 1)

        cset = csets[0]
        self.assertEqual(len(cset.entries), 7)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'scripts/trac-admin')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'setup.py')
        self.assertEqual(entry.action_kind, entry.UPDATED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'trac/scripts')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[3]
        self.assertEqual(entry.name, 'trac/scripts/__init__.py')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[4]
        self.assertEqual(entry.name, 'trac/scripts/admin.py')
        self.assertEqual(entry.action_kind, entry.RENAMED)
        self.assertEqual(entry.old_name, 'scripts/trac-admin')


    COPYFROM_AND_REMOVE_TEST = """\
<?xml version="1.0" encoding="utf-8"?>
<log>
<logentry
   revision="3170">
<author>abartlet</author>
<date>2004-10-24T23:54:00.078045Z</date>
<paths>
<path
   action="D">/branches/SAMBA_4_0/source/nsswitch/wins.c</path>
<path
   action="A">/branches/SAMBA_4_0/source/nsswitch/config.m4</path>
<path
   copyfrom-path="/branches/SAMBA_3_0/source/nsswitch"
   copyfrom-rev="3150"
   action="A">/branches/SAMBA_4_0/source/nsswitch</path>
<path
   action="M">/branches/SAMBA_4_0/source/nsswitch/wb_common.c</path>
</paths>
<msg>Add winbind client support back into Samba4.  This is to allow
auth_winbind to work, and to therefore use the new ntlm_auth and
GENSEC in an otherwise Samba3 setup.

I'm not quite sure what fun-and games my svn cp caused as I merged
this from samba_3_0, but anyway...

Andrew Bartlett
</msg>
</logentry>
</log>
"""

    def testCopyFromAndRemove(self):
        """Verify the svn parser handle copyfrom+remove"""

        log = StringIO(self.COPYFROM_AND_REMOVE_TEST)
        csets = changesets_from_svnlog(log,
                                       'http://svnanon.samba.org/samba',
                                       '/branches/SAMBA_4_0')

        self.assertEqual(len(csets), 1)

        cset = csets[0]
        self.assertEqual(len(cset.entries), 3)

        entry = cset.entries[0]
        self.assertEqual(entry.name, 'source/nsswitch')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[1]
        self.assertEqual(entry.name, 'source/nsswitch/config.m4')
        self.assertEqual(entry.action_kind, entry.ADDED)

        entry = cset.entries[2]
        self.assertEqual(entry.name, 'source/nsswitch/wb_common.c')
        self.assertEqual(entry.action_kind, entry.ADDED)
