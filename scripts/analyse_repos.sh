#!/bin/bash

# Git Commit Analysis Script for Glassey
# 
# This script analyzes git commits by author "Glassey" (case-insensitive) and generates
# a CSV report with the following metrics for each commit:
# - Commit hash, author, date, and subject
# - Number of lines inserted and deleted
# - Total lines changed (insertions + deletions)
# - Fix flag (T/F) indicating if the commit appears to fix an issue
#
# The fix detection looks for commit messages containing keywords like:
# "fix", "fixes", "close", "closed", "resolve", "resolved" followed by "#<number>"
#
# Output format: CSV with columns:
# commit,author,datetime,subject,insertions,deletions,total,fix

git log --author='[Gg]lassey' --date=iso \
  --pretty=format:'COMMIT%x09%h%x09%an%x09%ad%x09%s' --numstat \
| awk -F'\t' -v OFS=',' '
function quote(s){ gsub(/"/,"\"\"",s); return "\"" s "\"" }
BEGIN { print "commit,author,datetime,subject,insertions,deletions,total,fix" }
$1=="COMMIT" {
  if (NR>1) {
    print commit, author, date, quote(subject), ins, del, ins+del, fix
  }
  commit=$2; author=$3; date=$4; subject=$5
  ins=del=0; fix="F"
  # mark Fix if subject matches closing keyword
  if (tolower(subject) ~ /(fixe?s?|close[sd]?|resolve[sd]?) #[0-9]+/) fix="T"
  next
}
NF==3 {                     # numstat lines
  if ($1 != "-") ins += $1+0
  if ($2 != "-") del += $2+0
}
END {
  if (commit!="") print commit, author, date, quote(subject), ins, del, ins+del, fix
}'