#!/bin/bash -v

# File: test-svn2svn-#113-directory-deletion-and-rename.sh
# needs: test-svn2svn.include
# 
# Test for converting revisions from Subversion and back to Subversion again.
# to moving files and than delete directory
# 
# small ERROR (found by compair the logs):
# The source from "rename" will be lose. Subversion deletes the old path and creates the file as new in other path.
#
# First log:
#   Changed paths:
#      D /project-a/dir1
#      A /project-a/dir2/a (from /project-a/dir1/a:2)
#      A /project-a/dir2/b (from /project-a/dir1/b:2)
#
# second log:
#   Changed paths:
#      D /project-a/dir1
#      A /project-a/dir2/a
#      A /project-a/dir2/b
#   
# ####
#
# File state is OK. Only the log is not complete.


. ./test-svn2svn.include
subversion_setup

# checkout initial version
svn checkout file://$POSITORY/project-a my-project
cd my-project

# Create 2 revisions with directory remove and rename

# Ticket #113:
# * rename dir1/a dir2/a
# * rename dir1/b dir2/b
# * delete dir1

mkdir dir1
touch dir1/a
touch dir1/b
mkdir dir2
svn add dir1 dir2
svn commit --message "initial commit"

svn rename dir1/a dir2/a
svn rename dir1/b dir2/b
svn delete dir1
svn commit --message "file and directory removed after moving files outside"

testing_runs
