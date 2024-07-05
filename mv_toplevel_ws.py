#!/usr/bin/env python3

"""
Moves the focused container to the top-level container of the specified
workspace
"""

import i3ipc
import sys

from typing import List

def _get_toplevel_containers(ws: i3ipc.con.Con) -> List[i3ipc.con.Con]:
    """ Provided ws must have a single top-level container """
    assert ws.type == "workspace"
    # Crashes if there's not exactly 1 top-level container
    return [cont for cont in ws.nodes if cont.type == 'con']

def main(ws_name: str):
    """ Workspaces are assumed to be prefixed
    with an integer followed by a boundary character
    This means that 1 will match "1 foo" but not "10 bar"
    """
    conn = i3ipc.Connection()
    wses = [ws for ws in conn.get_tree().workspaces() if ws.name == ws_name]
    assert len(wses) < 2, f"Could not unambiguously identify workspace between: {wses}"
    # Get top-level container of the first matching workspace
    tlcs = _get_toplevel_containers(wses[0]) if len(wses) else []

    if len(wses) and len(tlcs) == 1:
        # We have an unambiguous workspace and TLC
        conn.command(f"[con_id={tlcs[0].id}] mark __target")
        conn.command(f"move container to mark __target")
        conn.command("[con_mark=__target] unmark") 
    else:
        # There was either no matching ws in the tree, which means it's empty
        # or we have multiple TLCs
        # Fall back to regular command
        conn.command(f"move container to workspace number {ws_name}")

if __name__ == "__main__":
    assert len(sys.argv) == 2
    try:
        main(sys.argv[1])
    except Exception as e:
        with open("/tmp/mv_toplevel_ws_faillog", "w") as f:
            f.write(str(e))
            f.flush()
