#!/bin/bash -v

# File: test-mtn2svn-umlaut-POSIX.sh
# needs: test-mtn2svn.include
# 
# Test for converting from Monotone to Subversion and back to Monotone again.
#
# Works after fixup LANG and using "automate certs" inside Tailor.

. ./test-mtn2svn.include

monotone_setup

# Create one file and 2 revisions, simple linear revisions

# Must be German, because testing Umlauts here (in html &auml; &ouml; ...)
export LANG="de_DE.UTF-8"

echo "Umlaut ä ö ü ß Ä Ö Ü" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit, Umlauts in file"

echo "foo" > file.txt
mtn_exec commit --message "change file (Umlauts ä ö ü ß Ä Ö Ü in changelog)"

# Test Tailor with locale POSIX now
export LANG="POSIX"

testing_runs
