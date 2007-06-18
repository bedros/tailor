#!/bin/bash -v

# File: test-mtn2mtn-tag.sh
# needs: test-mtn2mtn.include
# 
# Test for converting 3 revisions with 1 tag from Monotone to Monotone self.
# It's a selfchecking for Monotone.  Diff between test1.log and test2.log
# should no have difference.
#
# No errors found.
# Log-diff: PASS

. ./test-mtn2mtn.include
monotone_setup

# Create one file and 3 simple linear revisions

echo "foo" > file.txt
mtn_exec add file.txt
mtn_exec commit --message "initial commit"

echo "bar" > file.txt
mtn_exec commit --message "second commit with tag"

head=`mtn_exec automate get_base_revision_id`
mtn_exec tag $head "Tagged-with-number-1.0"

testing_runs
