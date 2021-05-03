#!/bin/bash

## Focuses the window whose title is a superset of the first argument to the script.
## Multiple matches picks the first one found (no order guaranteed)

# TODO: Handle multiple matches better.

if [ "$#" -ne 1 ]
then
    echo "Wrong number of arguments"
    echo "Usage: i3_focus_window.sh searchstring"
    exit 1
fi

i3-msg [title=\"\(?i\)$1\"] focus
