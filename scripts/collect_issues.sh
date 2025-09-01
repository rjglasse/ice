#!/bin/bash

gh issue list --state all --json number,title,state,createdAt \
  | jq -r '.[] | [.number, .title, .state, .createdAt] | @csv'