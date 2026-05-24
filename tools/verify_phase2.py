# -*- coding: utf-8 -*-
"""Phase 2 verification — inspect lifecycle state without changing it.

After Plugin Reloader, this is a safe read-only inspector. To exercise the
mechanic, use the toggle button in QGIS — that's what real users do.

Run from the QGIS Python Console:

    from pathlib import Path
    exec(compile(
        Path(r'C:\\Users\\br8kw\\Github\\QGISModes\\tools\\verify_phase2.py').read_text(),
        'verify_phase2.py', 'exec',
    ))
"""

import qgis.utils

PLUGIN_NAME = "qgismodes"


def _hdr(t):
    print("=" * 60)
    print(t)
    print("=" * 60)


_hdr("QGIS Modes — Phase 2 state inspector")

if PLUGIN_NAME not in qgis.utils.plugins:
    print(f"{PLUGIN_NAME!r} is not loaded. Run install_dev_link.py first.")
else:
    qm = qgis.utils.plugins[PLUGIN_NAME]

    print()
    print("--- Phase 2 components present? ---")
    print(f"qm.applier:   {type(getattr(qm, 'applier', None)).__name__}")
    print(f"qm.lifecycle: {type(getattr(qm, 'lifecycle', None)).__name__}")

    if not hasattr(qm, "lifecycle"):
        print()
        print("Lifecycle not wired — Phase 2 not loaded; run Plugin Reloader.")
    else:
        lc = qm.lifecycle

        print()
        print("--- StateStore (persisted intent) ---")
        print(f"enabled()         -> {qm.state_store.enabled()}")
        print(f"active_mode_id()  -> {qm.state_store.active_mode_id()}")
        toolbars, panels = qm.state_store.original_layout()
        print(f"captured layout   -> {len(toolbars)} toolbars, {len(panels)} panels")

        print()
        print("--- LifecycleController (in-memory state) ---")
        print(f"is_currently_applied() -> {lc.is_currently_applied()}")
        print(f"prev_ctx_menu_policy   -> {lc._prev_ctx_menu_policy}")
        print(f"last_known_good_mode   -> {lc._last_known_good_mode_id}")
        print(f"default_mode_id        -> {lc._default_mode_id()}")

        print()
        print("--- ModeApplier (owned toolbars) ---")
        print(f"owned_toolbar_names    -> {qm.applier.owned_toolbar_names}")

        print()
        print("--- Live UI snapshot ---")
        from qgis.PyQt.QtWidgets import QToolBar, QDockWidget
        mw = qm.mainwindow
        visible_toolbars = [
            tb.objectName() for tb in mw.findChildren(QToolBar)
            if tb.parent() == mw and not tb.isHidden() and tb.objectName()
        ]
        visible_panels = [
            d.objectName() for d in mw.findChildren(QDockWidget)
            if not d.isHidden() and d.objectName()
        ]
        print(f"menu_bar visible       -> {mw.menuBar().isVisible()}")
        print(f"context_menu_policy    -> {int(mw.contextMenuPolicy())}")
        print(f"visible toolbars ({len(visible_toolbars)}): {visible_toolbars}")
        print(f"visible panels   ({len(visible_panels)}): {visible_panels}")

    print()
    _hdr("How to exercise Phase 2")
    print("""
1. Click the QGIS Modes toggle button (toolbar or View menu).
   -> Should enter simplified mode: menu bar hidden, standard toolbars hidden,
      mode toolbars appear, exit button visible at end of the main toolbar.

2. Re-run this script to inspect state in simplified mode.

3. Click the in-toolbar exit (the QGIS Modes icon at the end of the main
   toolbar) -- or the toggle button again.
   -> Should restore the standard QGIS interface exactly as before.

4. Restart QGIS while in simplified mode.
   -> Should resume in the same mode after init completes (FR-LC-6).

If something breaks, paste the relevant Log Messages -> 'QGIS Modes' tab
content for the time window of the failure.
""")
