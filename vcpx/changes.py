#! /usr/bin/python
# -*- mode: python; coding: utf-8 -*-
# :Progetto: vcpx -- Changesets 
# :Creato:   ven 11 giu 2004 15:31:18 CEST
# :Autore:   Lele Gaifax <lele@nautilus.homeip.net>
# :Licenza:  GNU General Public License
# 

"""
Changesets are an object representation of a set of changes to some files.
"""

__docformat__ = 'reStructuredText'

class ChangesetEntry(object):
    """
    Represent a changed entry in a Changeset.

    For our scope, this simply means an entry `name`, the original
    `old_revision`, the `new_revision` after this change, an
    `action_kind` to denote the kind of change, and finally a `status`
    to indicate possible conflicts.
    """
    
    ADDED = 'ADD'
    DELETED = 'DEL'
    UPDATED = 'UPD'
    RENAMED = 'REN'

    APPLIED = 'APPLIED'
    CONFLICT = 'CONFLICT'
    
    __slots__ = ('name', 'old_name',
                 'old_revision', 'new_revision',
                 'action_kind', 'status')

    def __init__(self, name):
        self.name = name
        self.old_name = None
        self.old_revision = None
        self.new_revision = None
        self.action_kind = None
        self.status = None

    def __str__(self):
        if self.action_kind == self.ADDED:
            return '%s (new at %s)' % (self.name, self.new_revision)
        elif self.action_kind == self.DELETED:
            return '%s (deleted)' % self.name
        elif self.action_kind == self.UPDATED:
            return "%s (update to %s)" % (self.name,
                                          self.new_revision)
        else:
            return '%s (rename from %s)' % (self.name, self.old_name)


from textwrap import TextWrapper
from re import compile, MULTILINE
    
itemize_re = compile('^[ ]*[-*] ', MULTILINE)

def refill(msg):
    """
    Refill a changelog message.

    Normalize the message reducing multiple spaces and newlines to single
    spaces, recognizing common form of `bullet lists`, that is paragraphs
    starting with either a dash "-" or an asterisk "*".
    """
    
    wrapper = TextWrapper()
    res = []
    items = itemize_re.split(msg.strip())
    
    if len(items)>1:
        # Remove possible first empty split, when the message immediately
        # starts with a bullet
        if not items[0]:
            del items[0]
            
        if len(items)>1:
            wrapper.initial_indent = '- '
            wrapper.subsequent_indent = ' '*2
                
    for item in items:
        if item:
            words = filter(None, item.strip().replace('\n', ' ').split(' '))
            normalized = ' '.join(words)
            res.append(wrapper.fill(normalized))

    return '\n\n'.join(res)


class Changeset(object):
    """
    Represent a single upstream Changeset.

    This is a container of each file affected by this revision of the tree.
    """

    REFILL_MESSAGE = True
    """Refill changelogs"""
    
    def __init__(self, revision, date, author, log, entries=None, **other):
        """
        Initialize a new ChangeSet.
        """
        
        self.revision = revision
        self.date = date
        self.author = author
        if self.REFILL_MESSAGE:
            self.log = refill(log)
        else:
            self.log = log
        self.entries = entries or []

    def addEntry(self, entry, revision):
        """
        Facility to add an entry.
        """

        e = ChangesetEntry(entry)
        e.new_revision = revision
        self.entries.append(e)
        return e
    
    def __str__(self):
        s = []
        s.append('Revision: %s' % self.revision)
        s.append('Date: %s' % str(self.date))
        s.append('Author: %s' % self.author)
        for ak in ['Modified', 'Removed', 'Renamed', 'Added']:
            entries = getattr(self, ak.lower()+'Entries')()
            if entries:
                s.append('%s: %s' % (ak, ','.join([e.name
                                                   for e in entries])))
        s.append('Log: %s' % self.log)
        return '\n'.join(s)

    def addedEntries(self):
        """
        Filter the changesets and extract the added entries.
        """
        
        return [e for e in self.entries if e.action_kind == e.ADDED]

    def modifiedEntries(self):
        """
        Filter the changesets and extract the modified entries.
        """

        return [e for e in self.entries if e.action_kind == e.UPDATED]

    def removedEntries(self):
        """
        Filter the changesets and extract the deleted entries.
        """

        return [e for e in self.entries if e.action_kind == e.DELETED]

    def renamedEntries(self):
        """
        Filter the changesets and extract the renamed entries.
        """

        return [e for e in self.entries if e.action_kind == e.RENAMED]
