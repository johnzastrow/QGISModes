# -*- coding: utf-8 -*-
"""Phase 3c verification — inspect ImportExportService wiring + sanity checks.

Read-only. Most of Phase 3c is exercised interactively through the
SplitButton dropdown / menu-bar menu (file pickers, modal dialogs). This
script confirms only the structural wiring:

  * the service component is on the plugin,
  * UIWidgets has a back-edge to the service,
  * the service points at the user modes dir,
  * the dialog adapter callables on UIWidgets are reachable.

The interactive section below describes a quick end-to-end exercise:
    export the default mode, hand-edit it, re-import (overwrite + keep-both).

Run from the QGIS Python Console:

    from pathlib import Path
    exec(compile(
        Path(r'C:\\Users\\br8kw\\Github\\QGISModes\\tools\\verify_phase3c.py').read_text(),
        'verify_phase3c.py', 'exec',
    ))
"""

import qgis.utils

PLUGIN_NAME = "qgismodes"


def _hdr(t):
    print("=" * 60)
    print(t)
    print("=" * 60)


_hdr("QGIS Modes — Phase 3c state inspector")

if PLUGIN_NAME not in qgis.utils.plugins:
    print(f"{PLUGIN_NAME!r} is not loaded. Run install_dev_link.py first.")
else:
    qm = qgis.utils.plugins[PLUGIN_NAME]

    print()
    print("--- ImportExportService wired? ---")
    svc = getattr(qm, "importexport", None)
    print(f"qm.importexport: {type(svc).__name__}")
    if svc is None:
        print()
        print("Service not wired — Phase 3c not loaded; run Plugin Reloader.")
    else:
        print(f"uiwidgets.importexport is qm.importexport: "
              f"{qm.uiwidgets.importexport is svc}")
        print(f"user_dir: {svc.user_dir!r}")
        print(f"dialog callables:")
        print(f"  conflict_dialog : {callable(svc.conflict_dialog)}")
        print(f"  requires_dialog : {callable(svc.requires_dialog)}")
        print(f"  on_batch_complete: {callable(svc.on_batch_complete)}")

        print()
        print("--- StateStore.last_export_dir ---")
        print(f"value: {qm.state_store.last_export_dir()!r}")

        print()
        print("--- Registry ---")
        print(f"modes installed: "
              f"{[mid for mid, _, _ in qm.registry.available_modes()]}")
        print(f"shortcuts in sync: "
              f"{sorted(qm.shortcuts._switch_actions.keys()) == sorted(mid for mid, _, _ in qm.registry.available_modes())}")

    print()
    _hdr("How to exercise Phase 3c")
    print(r"""
A. Export round-trip (quickest smoke test)
   1. Toggle dropdown → 'Export modes…' → tick 'Default' → OK → pick a temp
      folder (e.g. C:\Users\<you>\Desktop).
      -> Message bar: "1 exported, 0 failed."
      -> File on disk: <folder>\default.json (identical bytes to the
         shipped/user copy).

B. Conflict → Overwrite
   1. Edit the exported default.json — change "name" to "DefaultEdited".
   2. Toggle dropdown → 'Import mode…' → select the edited file.
      -> ConflictDialog appears ("A mode with id 'default' is already
         installed"). Click Overwrite.
      -> Message bar: "1 imported, 0 skipped."
   3. Re-run this script (or open the dropdown): the mode should now appear
      as 'DefaultEdited' (active-mark still works).

C. Conflict → Keep both
   1. Import the same edited file again.
      -> ConflictDialog → Keep both.
      -> A new file <user>/qgismodes/modes/default-1.json appears.
      -> Registry now lists two modes; InlineModeSwitcher should now inject
         on next 'enter simplified mode'.

D. Folder import
   1. Drop two valid mode files into a fresh folder.
   2. Toggle dropdown → 'Import folder…' → select the folder.
      -> Both imported in one batch; message bar reports the count.

E. Failure modes
   * Import a malformed .json — should be skipped with a load-failure
     reason; message bar shows "0 imported, 1 skipped".
   * Cancel out of the ConflictDialog — that file is skipped, the rest of
     the batch continues.
""")
