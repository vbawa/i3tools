#!/usr/bin/env python3

"""
Switches operational modes of OS by disabling workspaces.  Currently supports work and recreational
mode, which respectively disable recreational and work workspaces.

Usage:
    switch_mode.py MODE

where MODE is either "WORK", "REC", or "ALL" (case insensitive).
"""

import enum
import os
import subprocess
import re
import sys

from typing import Iterable, List

I3_CONFIG_FILE = os.path.expanduser("~/.config/i3/config")

Mode = enum.Enum("Mode", ("WORK", "REC", "ALL"))
# TODO: Switch to whitelist
DISABLED_WS_IDS_BY_MODE = {Mode.WORK: (3, 6), Mode.REC: (1, 4, 5), Mode.ALL: ()}

ALL_WSES = tuple(range(1, 11))


def _is_enabling_ln(ws_ids: int, ln: str):
    """ Returns whether `ln` is the line enabling the ws identified by `ws_id` """
    ws_ids_pattern = "(" + "|".join(map(str, ws_ids)) + ")"
    re_pattern = ".*bindsym \$mod\+. workspace number {} .*".format(ws_ids_pattern)
    re_match = re.match(re_pattern, ln)
    return re_match is not None


def _is_disabling_ln(ws_ids: int, ln: str) -> bool:
    # The shortcut for workspace 10 is 0
    shortcuts = [(0 if ws_id == 10 else ws_id)  for ws_id in ws_ids]
    shortcuts_pattern = "(" + "|".join(map(str, shortcuts)) + ")"
    re_pattern = ".*bindsym \$mod\+{} exec :.*".format(shortcuts_pattern)
    return re.match(re_pattern, ln) is not None


def _turn_on_ln(ln: str) -> str:
    # Adds newline back in because the strip() takes it out
    return ln.lstrip(" #").strip() + "\n"


def _turn_off_ln(ln: str) -> str:
    # Turn the line on to normalize it, then disable it.
    return "# " + _turn_on_ln(ln)


def switch_wses(
    ws_ids: Iterable[int], config_lns: Iterable[str], enable: bool
) -> List[str]:
    """ Enable or disable the provided workspace IDs """
    if len(ws_ids) == 0:
        return config_lns

    out_lines = list(config_lns)
    del config_lns

    # Enabling lines are turned on and disabling lines are turned off
    # The function to apply to ws-disabling lines
    disabling_change_fn = _turn_off_ln if enable else _turn_on_ln
    # The function to apply to ws-enabling lines
    enabling_change_fn = _turn_on_ln if enable else _turn_off_ln

    for i_ln, ln in enumerate(out_lines):
        new_ln = None
        if _is_enabling_ln(ws_ids, ln):
            new_ln = enabling_change_fn(ln)
        elif _is_disabling_ln(ws_ids, ln):
            new_ln = disabling_change_fn(ln)

        if new_ln is not None:
            # Updates output line
            out_lines[i_ln] = new_ln
            # TODO: I can reconfigure this to know which WS is being updated, and once every one has
            # been updated twice, I can return early.

    return out_lines


def switch_mode(mode: Mode, in_filename: str = I3_CONFIG_FILE, out_filename: str = None):
    out_filename = out_filename or in_filename

    with open(in_filename, "r") as rf:
        config_lns = rf.readlines()

    # TODO: This can be done in one pass. Refactor it to do so.
    config_lns = switch_wses(ALL_WSES, config_lns, enable=True)

    ws_ids = DISABLED_WS_IDS_BY_MODE[mode]
    config_lns = switch_wses(ws_ids, config_lns, enable=False)

    with open(out_filename, "w") as wf:
        config_lns = wf.writelines(config_lns)


if __name__ == "__main__":
    assert len(sys.argv) == 2
    switch_mode(Mode[sys.argv[1].upper()])
    subprocess.check_call("i3-msg reload".split(" "))
