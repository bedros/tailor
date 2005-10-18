#!tailor
'''
[DEFAULT]
verbose = False
target-module = None
projects = project2

[project1]
root-directory = /tmp/tailor-tests
source = svn:project1repo
target = darcs:project1repo
refill-changelogs = Yes
state-file = project1.state
before-commit = (maybe_skip, refill, p1_remap_authors)
after-commit = checkpoint

[svn:project1repo]
repository = svn://some.server/svn
module = project1
use-propset = Yes

[darcs:project1repo]
repository = ~/darcs/project1

[monotone:project1repo]
repository = /tmp/db
passphrase = simba

[project2]
root-directory = /tmp/tailor-tests
source = darcs:project1repo
target = svn:project2repo
refill-changelogs = Yes
state-file = project2.state
before-commit = refill

[svn:project2repo]

[project3]
root-directory = /tmp/tailor-tests
source = svndump:project3repo
target = darcs:project3repo

[svndump:project3repo]
repository = %(tailor_repo)s/vcpx/tests/data/simple.svndump
subdir = plain

[darcs:project3repo]
subdir = .

[project4]
source = svndump:project3repo
target = darcs:project4repo

[darcs:project4repo]
subdir = darcs
'''

def maybe_skip(context, changeset):
    for e in changeset.entries:
        if not context.darcs.isBoringFile(e):
            return True
    # What a bunch of boring entries! Skip the patch
    return False

def refill(context, changeset):
    changeset.refillChangelog()
    return True

p1_authors_map = {
    'lele': 'Lele Gaifax <lele@example.com>',
    'x123': 'A man ... with a name to come',
}

def p1_remap_authors(context, changeset):
    if p1_authors_map.has_key(changeset.author):
        changeset.author = p1_authors_map[changeset.author]
    return True

def checkpoint(context, changeset):
    if changeset.log.startswith('Release '):
        context.target.tagWithCheckpoint(changeset.log)
    return True
