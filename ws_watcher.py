#!/usr/bin/env python3

from typing import Callable, Iterable, Optional

import asyncio
import i3ipc
import i3ipc.aio
import subprocess
import tqdm

"""
Hides all windows when leaving any workspace, and show when entering.
Chrome/ium doesnt consider itself hidden when on an invisible workspace,
and treats the tabs as if they're visible (ie doesn't throttle CPU usage).
This cuts my idle CPU usage by ~80%, per htop

Adapted from https://gist.github.com/raidzero/2e2a947a181de98052f2910a5b79eaf9

Runs on Python 3.6
"""


import sys

# TODO: This breaks on >3.6.  Verify before using with other versions
assert sys.version_info.major == 3 and sys.version_info.minor == 6

HIDDEN = '_NET_WM_STATE_HIDDEN'
SHOWN = '_NET_WM_STATE_SHOWN'

class LruCache:
    def __init__(self, max_size: int):
        self.cache = []
        self.max_size = max_size

    def insert(self, val: int) -> Optional[int]:
        """ Returns number of removed workspace, if any. """
        try:
            # Avoid dupes
            self.cache.remove(val)
        except ValueError:
            pass
        self.cache.append(val)

        removed = None
        # If full, remove oldest (head of list)
        if len(self.cache) > self.max_size:
            removed = self.cache.pop(0)
        return removed


    def __contains__(self, val):
        return self.cache.__contains__(val)

RECENTLY_USED = LruCache(max_size=3)
NEVER_HIDE = set((9, 10))

# TODO: Consistent formatting of fxn names.
# TODO: This is reaaaallly slow, even slower than synchronous somehow...
async def showWindows(windows: Iterable[i3ipc.Con], task_limit=8):
    async def show(win_id: int):
        subprocess.call(f"xprop -id {win_id} -f _NET_WM_STATE 32a -remove {HIDDEN}".split(" "))
        subprocess.call(
            f"xprop -id {win_id} -f _NET_WM_STATE 32a -set _NET_WM_STATE {SHOWN}".split(" ")
        )

    print(f"Showing {len(windows)} windows")
    for w in tqdm.tqdm(windows):
        asyncio.ensure_future(show(w.window))

async def hideWindows(windows: Iterable[int], task_limit=8):
    async def hide(win_id: int):
        subprocess.call(f"xprop -id {win_id} -f _NET_WM_STATE 32a -remove {SHOWN}".split(" "))
        subprocess.call(
            f"xprop -id {win_id} -f _NET_WM_STATE 32a -set _NET_WM_STATE {HIDDEN}".split(" ")
        )

    print(f"Hiding {len(windows)} windows")
    for w in tqdm.tqdm(windows):
        asyncio.ensure_future(hide(w.window))

async def onWorkspace(i3, event):
    if event.change in ['focus']:
        # Old and new workspaces
        new_ws = event.current
        if new_ws.num not in RECENTLY_USED:
            print(f"showing WS {new_ws.num}")
            # Wait for show to complete before starting hiding
            await showWindows(new_ws.leaves())

        removed_ws = RECENTLY_USED.insert(new_ws.num)
        if removed_ws is not None and removed_ws not in NEVER_HIDE:
            # Only hide it if we haven't used it in a while.
            t = await i3.get_tree()
            wins = [w for w in t.leaves() if w.workspace().num == removed_ws]
            print(f"hiding WS {removed_ws}")
            await hideWindows(wins)

def getFocusedWorkspace(i3):
    (ws_num,) = (ws.num for ws in i3.get_workspaces() if ws.focused)
    return ws_num

async def monitor_loop():
    print("starting monitor loop", flush=True)
    i3 = await i3ipc.aio.Connection(auto_reconnect=True).connect()
    i3.on("workspace", onWorkspace)
    await i3.main()

async def main(cmd: str):
    if cmd == "showall":
        # TODO: This is super, super slow and hangs the system
        # even when using asyncio. Figure out where the performance gap is
        # and fix it (I assume it's in the xprop calls)
        i3 = i3ipc.Connection(auto_reconnect=True)
        wins = i3.get_tree().leaves()
        await showWindows(wins)
    elif cmd == "hideall":
        i3 = i3ipc.Connection(auto_reconnect=True)
        # These two are synchronous, consider making async
        focused_ws_num = getFocusedWorkspace(i3)
        wins = i3.get_tree().leaves()
        # To be safe, don't hide current ws's windows
        wins_to_hide = [w for w in wins if w.workspace().num != focused_ws_num]
        await hideWindows(wins_to_hide)
    # TODO: Proper cleanup upon end of program (showAll)
    else:
        raise NotImplementedError(f"Unrecognized command {cmd}")

if __name__ == "__main__":
    (cmd,) = sys.argv[1:]
    # TODO: Cleanup command handling and fxn interfaces
    if cmd == "monitor":
        asyncio.get_event_loop().run_until_complete(monitor_loop())
    else:
        asyncio.get_event_loop().run_until_complete(main(cmd))
