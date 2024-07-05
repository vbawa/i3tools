#!/usr/bin/env python3

"""
Switches operational modes of OS by disabling workspaces.  Currently supports work and recreational
mode, which respectively disable recreational and work workspaces.

Usage:
    switch_mode.py MODE_STR

The valid modes are "WORK", "REC", and "ALL"
MODE_STR can be a case-insensitive prefix of any of these modes. It can also
be a comma-separated list of valid workspaces, to which the usable set of
workspaces will be restricted.
"""

import enum
import os
import subprocess
import re
import sys

from typing import Iterable, List, Tuple

I3_CONFIG_FILE = os.path.expanduser("~/.config/i3/config")

Mode = enum.Enum("Mode", ("WORK", "REC", "FOCUS", "ALL"))
# TODO: Switch to whitelist
# Custom modes consist of a comma-separated list of numbers, specifying a whitelist of WSes
DISABLED_WS_IDS_BY_MODE = {
    Mode.WORK: (3, 6),
    Mode.REC: (1, 4, 5),
    Mode.FOCUS: (1, 3, 6),
    Mode.ALL: (),
}

ALL_WSES = tuple(range(1, 11))


def _is_enabling_ln(ws_ids: int, ln: str):
    """ Returns whether `ln` is the line enabling the ws identified by `ws_id` """
    ws_ids_pattern = "(" + "|".join(map(str, ws_ids)) + ")"
    # The final group means that the pattern can either terminate, or there can
    # be a space after the number, with some more text afterwards.
    re_pattern = ".*bindsym \$mod\+. workspace number {}(\s.*\n|\n)".format(ws_ids_pattern)
    re_match = re.match(re_pattern, ln)
    return re_match is not None


def _is_disabling_ln(ws_ids: int, ln: str) -> bool:
    # The shortcut for workspace 10 is 0
    shortcuts = [(0 if ws_id == 10 else ws_id) for ws_id in ws_ids]
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


def _parse_custom_ids(mode_str: str) -> Tuple[int]:
    """ Expects a comma-separated list of WS IDs to _enable_ and returns their complement,
    representing the IDs to _disable_ """
    enable_ids = set(int(x) for x in mode_str.strip().split(","))
    assert(all(ws_id in ALL_WSES for ws_id in enable_ids))
    return tuple(set(ALL_WSES) - enable_ids)


def switch_mode(
    mode_str: Mode, in_filename: str = I3_CONFIG_FILE, out_filename: str = None
):
    out_filename = out_filename or in_filename

    with open(in_filename, "r") as rf:
        config_lns = rf.readlines()

    # TODO: This can be done in one pass. Refactor it to do so.
    # Enable all to normalize
    config_lns = switch_wses(ALL_WSES, config_lns, enable=True)

    key = mode_str.upper()
    ws_ids_to_disable = (
        DISABLED_WS_IDS_BY_MODE[Mode[key]]
        if key in Mode.__dict__
        else _parse_custom_ids(mode_str)
    )
    config_lns = switch_wses(ws_ids_to_disable, config_lns, enable=False)

    with open(out_filename, "w") as wf:
        config_lns = wf.writelines(config_lns)


if __name__ == "__main__":
    assert len(sys.argv) == 2
    switch_mode(sys.argv[1])
    subprocess.check_call("i3-msg reload".split(" "))
