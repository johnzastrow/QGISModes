# -*- coding: utf-8 -*-
"""Diagnose a qgismodes plugin-load failure by importing manually.

Use when `startPlugin` returns False — this script catches the exception inline
and prints the full traceback (instead of leaving it in the QGIS log).

Run from the QGIS Python Console:

    from pathlib import Path
    exec(compile(
        Path(r'C:\\Users\\br8kw\\Github\\QGISModes\\tools\\diagnose_load.py').read_text(),
        'diagnose_load.py', 'exec',
    ))
"""

import sys
import traceback

import qgis.utils

PLUGIN_NAME = "qgismodes"


def _hdr(t):
    print()
    print("=" * 60)
    print(t)
    print("=" * 60)


_hdr("State before diagnosis")
print(f"available_plugins  contains {PLUGIN_NAME!r}: "
      f"{PLUGIN_NAME in qgis.utils.available_plugins}")
print(f"sys.modules        contains {PLUGIN_NAME!r}: "
      f"{PLUGIN_NAME in sys.modules}")
print(f"qgis.utils.plugins contains {PLUGIN_NAME!r}: "
      f"{PLUGIN_NAME in qgis.utils.plugins}")
print(f"active_plugins     contains {PLUGIN_NAME!r}: "
      f"{PLUGIN_NAME in qgis.utils.active_plugins}")


# Clear any cached modules so we always do a fresh import.
_hdr("Clearing module cache for fresh import")
removed = []
for k in list(sys.modules.keys()):
    if k == PLUGIN_NAME or k.startswith(PLUGIN_NAME + "."):
        del sys.modules[k]
        removed.append(k)
print(f"Removed {len(removed)} cached module(s): {removed}")


# Step A — raw import
_hdr(f"Step A: import {PLUGIN_NAME!r}")
module = None
try:
    __import__(PLUGIN_NAME)
    module = sys.modules.get(PLUGIN_NAME)
    print(f"OK — module = {module}")
    print(f"  has classFactory: {hasattr(module, 'classFactory')}")
    print(f"  __file__         : {getattr(module, '__file__', '(no __file__)')}")
except Exception:
    print("IMPORT FAILED:\n")
    traceback.print_exc()
    print("\nStop. Fix the import error, reload (Plugin Reloader), re-run.")


# Step B — classFactory
plugin = None
if module is not None and hasattr(module, "classFactory"):
    _hdr("Step B: classFactory(iface)")
    try:
        plugin = module.classFactory(qgis.utils.iface)
        print(f"OK — plugin = {plugin}")
        print(f"  type:           {type(plugin).__name__}")
        print(f"  has initGui:    {hasattr(plugin, 'initGui')}")
        print(f"  has unload:     {hasattr(plugin, 'unload')}")
    except Exception:
        print("classFactory FAILED:\n")
        traceback.print_exc()


# Step C — initGui
if plugin is not None and hasattr(plugin, "initGui"):
    _hdr("Step C: initGui()")
    try:
        plugin.initGui()
        print("OK — initGui completed")
        # Register so subsequent verify_phase1.py runs see it
        qgis.utils.plugins[PLUGIN_NAME] = plugin
        if PLUGIN_NAME not in qgis.utils.active_plugins:
            qgis.utils.active_plugins.append(PLUGIN_NAME)
        print(f"Registered in qgis.utils.plugins[{PLUGIN_NAME!r}]")
    except Exception:
        print("initGui FAILED:\n")
        traceback.print_exc()


_hdr("State after diagnosis")
print(f"qgis.utils.plugins contains {PLUGIN_NAME!r}: "
      f"{PLUGIN_NAME in qgis.utils.plugins}")
print(f"active_plugins     contains {PLUGIN_NAME!r}: "
      f"{PLUGIN_NAME in qgis.utils.active_plugins}")
print()
print("If a step above shows a traceback, paste it back and we'll fix the code.")
